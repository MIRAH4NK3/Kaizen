from fastapi import FastAPI, APIRouter, UploadFile, File, Form, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import boto3
import json
import asyncio
import aiofiles
import tempfile

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# AWS clients setup
aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY')
aws_region = os.environ.get('AWS_REGION', 'eu-central-1')
s3_bucket_name = os.environ.get('S3_BUCKET_NAME', 'kaizen-voice-recordings')

transcribe_client = boto3.client(
    'transcribe',
    region_name=aws_region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

bedrock_client = boto3.client(
    'bedrock-runtime',
    region_name=aws_region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

s3_client = boto3.client(
    's3',
    region_name=aws_region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

# Create the main app without a prefix
app = FastAPI(title="Kaizen Voice Recorder API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class KaizenSuggestion(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    job_id: str
    transcript: str
    summary: str
    lean_category: str
    suggestion_level: str
    reasoning: Optional[str] = None
    location: Optional[str] = None
    shift: Optional[str] = None
    associate_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending_review"

class KaizenSuggestionCreate(BaseModel):
    location: Optional[str] = None
    shift: Optional[str] = None
    associate_name: Optional[str] = None

class ProcessingStatus(BaseModel):
    job_id: str
    status: str
    message: str

# Health check endpoint
@api_router.get("/health")
async def health_check():
    try:
        # Check MongoDB connection
        await db.command("ping")
        
        # Check AWS credentials (quick test)
        try:
            transcribe_client.list_transcription_jobs(MaxResults=1)
            aws_status = "healthy"
        except Exception as e:
            aws_status = f"error: {str(e)}"
        
        return {
            "status": "healthy", 
            "timestamp": datetime.utcnow(),
            "mongodb": "connected",
            "aws": aws_status
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")

@api_router.get("/")
async def root():
    return {"message": "Kaizen Voice Recorder API - Ready to capture your improvement ideas!"}

async def upload_to_s3(audio_file: UploadFile, s3_key: str):
    """Upload audio file to S3"""
    try:
        # Create bucket if it doesn't exist
        try:
            s3_client.head_bucket(Bucket=s3_bucket_name)
        except:
            try:
                s3_client.create_bucket(
                    Bucket=s3_bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': aws_region}
                )
            except Exception as e:
                logging.warning(f"Could not create bucket: {e}")
        
        # Reset file pointer to beginning
        await audio_file.seek(0)
        content = await audio_file.read()
        
        # Upload to S3
        s3_client.put_object(
            Bucket=s3_bucket_name,
            Key=s3_key,
            Body=content,
            ContentType='audio/webm'
        )
        
        return f"s3://{s3_bucket_name}/{s3_key}"
        
    except Exception as e:
        raise Exception(f"S3 upload failed: {str(e)}")

async def start_transcription_job(job_name: str, s3_uri: str) -> str:
    """Start AWS Transcribe job and wait for completion"""
    try:
        # Start transcription job
        transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': s3_uri},
            MediaFormat='webm',
            LanguageCode='en-US',
            OutputBucketName=s3_bucket_name,
            OutputKey=f"transcripts/{job_name}.json"
        )
        
        # Poll for completion (with timeout)
        max_wait_time = 300  # 5 minutes max
        poll_interval = 5  # Check every 5 seconds
        waited_time = 0
        
        while waited_time < max_wait_time:
            response = transcribe_client.get_transcription_job(
                TranscriptionJobName=job_name
            )
            status = response['TranscriptionJob']['TranscriptionJobStatus']
            
            if status == 'COMPLETED':
                # Download transcript from S3
                transcript_key = f"transcripts/{job_name}.json"
                
                try:
                    transcript_obj = s3_client.get_object(
                        Bucket=s3_bucket_name,
                        Key=transcript_key
                    )
                    transcript_data = json.loads(transcript_obj['Body'].read())
                    return transcript_data['results']['transcripts'][0]['transcript']
                except Exception as e:
                    raise Exception(f"Failed to download transcript: {str(e)}")
                    
            elif status == 'FAILED':
                failure_reason = response['TranscriptionJob'].get('FailureReason', 'Unknown error')
                raise Exception(f"Transcription job failed: {failure_reason}")
                
            # Wait before polling again
            await asyncio.sleep(poll_interval)
            waited_time += poll_interval
            
        raise Exception("Transcription job timed out")
        
    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")

async def analyze_with_claude(transcript: str, metadata: dict) -> dict:
    """Analyze transcript with Claude 3 Sonnet for Lean categorization"""
    try:
        prompt = f"""
        Analyze this workplace improvement suggestion transcript and provide a structured analysis.
        
        TRANSCRIPT: "{transcript}"
        CONTEXT:
        - Location: {metadata.get('location', 'Not specified')}
        - Shift: {metadata.get('shift', 'Not specified')}
        - Associate: {metadata.get('associate_name', 'Not specified')}
        
        Please categorize this suggestion according to Lean methodology and provide:
        1. A concise summary (2-3 sentences)
        2. Primary Lean waste category from: Motion, Waiting, Overproduction, Defects, Overprocessing, Inventory, Transportation
        3. Suggestion level: "Just Do It" (simple fix), "Needs Review" (requires approval), or "Safety" (safety concern)
        4. Brief reasoning for the categorization
        
        Respond ONLY in valid JSON format:
        {{
            "summary": "Brief summary of the improvement suggestion",
            "lean_category": "Primary lean waste category",
            "suggestion_level": "Just Do It|Needs Review|Safety",
            "reasoning": "Brief explanation of why this fits the category and level"
        }}
        """

        response = bedrock_client.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            })
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        # Parse JSON response from Claude
        try:
            analysis = json.loads(content)
            return analysis
        except json.JSONDecodeError as e:
            # Fallback if Claude doesn't return valid JSON
            return {
                "summary": transcript[:200] + "..." if len(transcript) > 200 else transcript,
                "lean_category": "Motion",
                "suggestion_level": "Needs Review",
                "reasoning": f"AI analysis failed, manual review needed. Error: {str(e)}"
            }
        
    except Exception as e:
        logging.error(f"Claude analysis failed: {str(e)}")
        # Fallback analysis
        return {
            "summary": transcript[:200] + "..." if len(transcript) > 200 else transcript,
            "lean_category": "Motion",
            "suggestion_level": "Needs Review",
            "reasoning": f"AI analysis unavailable: {str(e)}"
        }

async def store_suggestion(job_id: str, transcript: str, analysis: dict, metadata: dict) -> str:
    """Store processed suggestion in MongoDB"""
    try:
        document = {
            "id": str(uuid.uuid4()),
            "job_id": job_id,
            "transcript": transcript,
            "summary": analysis["summary"],
            "lean_category": analysis["lean_category"],
            "suggestion_level": analysis["suggestion_level"],
            "reasoning": analysis.get("reasoning", ""),
            "location": metadata.get("location"),
            "shift": metadata.get("shift"),
            "associate_name": metadata.get("associate_name"),
            "timestamp": datetime.utcnow(),
            "status": "pending_review"
        }
        
        result = await db.kaizen_suggestions.insert_one(document)
        return str(result.inserted_id)
        
    except Exception as e:
        raise Exception(f"Database storage failed: {str(e)}")

@api_router.post("/transcribe", response_model=dict)
async def process_voice_recording(
    audio: UploadFile = File(...),
    metadata: str = Form(default='{}')
):
    """Process voice recording: transcribe + AI analysis + storage"""
    try:
        # Parse metadata
        try:
            meta_data = json.loads(metadata)
        except json.JSONDecodeError:
            meta_data = {}
        
        # Validate audio file
        if not audio.filename:
            raise HTTPException(status_code=400, detail="No audio file provided")
        
        # Generate unique identifiers
        job_id = f"kaizen_{uuid.uuid4().hex[:8]}"
        s3_key = f"audio/{job_id}.webm"
        
        logging.info(f"Processing audio job: {job_id}")
        
        # Upload audio to S3
        s3_uri = await upload_to_s3(audio, s3_key)
        logging.info(f"Audio uploaded to S3: {s3_uri}")
        
        # Start transcription job
        transcription_result = await start_transcription_job(job_id, s3_uri)
        logging.info(f"Transcription completed: {len(transcription_result)} characters")
        
        # Process with Bedrock Claude
        analysis_result = await analyze_with_claude(transcription_result, meta_data)
        logging.info(f"AI analysis completed: {analysis_result['lean_category']}")
        
        # Store in MongoDB
        document_id = await store_suggestion(job_id, transcription_result, analysis_result, meta_data)
        logging.info(f"Stored in database: {document_id}")
        
        return {
            "success": True,
            "job_id": job_id,
            "document_id": document_id,
            "transcript": transcription_result,
            "summary": analysis_result["summary"],
            "lean_category": analysis_result["lean_category"],
            "suggestion_level": analysis_result["suggestion_level"],
            "reasoning": analysis_result.get("reasoning", "")
        }
        
    except Exception as e:
        logging.error(f"Processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@api_router.get("/suggestions", response_model=dict)
async def get_suggestions(skip: int = 0, limit: int = 20):
    """Retrieve stored suggestions for review"""
    try:
        # Get total count
        total = await db.kaizen_suggestions.count_documents({})
        
        # Get suggestions with pagination
        cursor = db.kaizen_suggestions.find().skip(skip).limit(limit).sort("timestamp", -1)
        suggestions = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string and format dates
        for suggestion in suggestions:
            suggestion["_id"] = str(suggestion["_id"])
            if isinstance(suggestion.get("timestamp"), datetime):
                suggestion["timestamp"] = suggestion["timestamp"].isoformat()
            
        return {
            "suggestions": suggestions,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        logging.error(f"Failed to retrieve suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve suggestions: {str(e)}")

@api_router.post("/suggestions/{suggestion_id}/status")
async def update_suggestion_status(suggestion_id: str, status: dict):
    """Update the status of a suggestion"""
    try:
        valid_statuses = ["pending_review", "approved", "implemented", "rejected"]
        new_status = status.get("status")
        
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        result = await db.kaizen_suggestions.update_one(
            {"id": suggestion_id},
            {"$set": {"status": new_status, "last_updated": datetime.utcnow()}}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Suggestion not found")
        
        return {"success": True, "message": f"Status updated to {new_status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Failed to update status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {str(exc)}")
    
    # Store error in MongoDB for monitoring
    try:
        await db.errors.insert_one({
            "error": str(exc),
            "endpoint": str(request.url),
            "method": request.method,
            "timestamp": datetime.utcnow()
        })
    except:
        pass  # Don't fail if error logging fails
    
    return HTTPException(status_code=500, detail="Internal server error occurred")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)