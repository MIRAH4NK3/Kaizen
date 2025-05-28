import React, { useState, useEffect } from 'react';
import { useReactMediaRecorder } from 'react-media-recorder';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

function App() {
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [currentView, setCurrentView] = useState('recorder'); // 'recorder' or 'tracker'
  const [metadata, setMetadata] = useState({
    location: '',
    shift: '',
    associate_name: ''
  });
  const [error, setError] = useState(null);

  const {
    status,
    startRecording,
    stopRecording,
    mediaBlobUrl,
    clearBlobUrl
  } = useReactMediaRecorder({
    audio: true,
    onStop: (blobUrl, blob) => handleUpload(blob)
  });

  // Load suggestions when switching to tracker view
  useEffect(() => {
    if (currentView === 'tracker') {
      loadSuggestions();
    }
  }, [currentView]);

  const handleUpload = async (audioBlob) => {
    if (!audioBlob || audioBlob.size === 0) {
      setError('No audio recorded. Please try again.');
      return;
    }

    setIsProcessing(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'kaizen-recording.webm');
      formData.append('metadata', JSON.stringify({
        location: metadata.location || 'Production Floor',
        shift: metadata.shift || 'Day Shift',
        associate_name: metadata.associate_name || 'Anonymous',
        timestamp: new Date().toISOString()
      }));

      const response = await fetch(`${BACKEND_URL}/api/transcribe`, {
        method: 'POST',
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }
      
      const data = await response.json();
      setResult(data);
      
      // Clear the form after successful submission
      clearBlobUrl();
      setMetadata({ location: '', shift: '', associate_name: '' });
      
    } catch (error) {
      console.error('Processing failed:', error);
      setError(`Failed to process recording: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const loadSuggestions = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/suggestions`);
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to load suggestions:', error);
    }
  };

  const updateSuggestionStatus = async (suggestionId, newStatus) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/suggestions/${suggestionId}/status`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus })
      });
      
      if (response.ok) {
        // Reload suggestions to reflect the change
        loadSuggestions();
      }
    } catch (error) {
      console.error('Failed to update status:', error);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending_review': return 'bg-yellow-100 text-yellow-800';
      case 'approved': return 'bg-green-100 text-green-800';
      case 'implemented': return 'bg-blue-100 text-blue-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Motion': 'bg-purple-100 text-purple-800',
      'Waiting': 'bg-orange-100 text-orange-800',
      'Overproduction': 'bg-red-100 text-red-800',
      'Defects': 'bg-pink-100 text-pink-800',
      'Overprocessing': 'bg-indigo-100 text-indigo-800',
      'Inventory': 'bg-teal-100 text-teal-800',
      'Transportation': 'bg-cyan-100 text-cyan-800'
    };
    return colors[category] || 'bg-gray-100 text-gray-800';
  };

  const getSuggestionLevelColor = (level) => {
    switch (level) {
      case 'Just Do It': return 'bg-green-100 text-green-800';
      case 'Needs Review': return 'bg-yellow-100 text-yellow-800';
      case 'Safety': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            🎤 Kaizen Voice Recorder
          </h1>
          <p className="text-gray-600 text-lg">
            Capture workplace improvement ideas with your voice
          </p>
        </div>

        {/* Navigation */}
        <div className="flex justify-center mb-8">
          <div className="bg-white rounded-lg p-1 shadow-md">
            <button
              onClick={() => setCurrentView('recorder')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                currentView === 'recorder'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:text-blue-500'
              }`}
            >
              🎙️ Record Idea
            </button>
            <button
              onClick={() => setCurrentView('tracker')}
              className={`px-6 py-2 rounded-md font-medium transition-colors ${
                currentView === 'tracker'
                  ? 'bg-blue-500 text-white'
                  : 'text-gray-600 hover:text-blue-500'
              }`}
            >
              📊 View Tracker
            </button>
          </div>
        </div>

        {currentView === 'recorder' ? (
          /* Voice Recorder View */
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <h2 className="text-2xl font-semibold text-gray-800 mb-6">Record Your Improvement Idea</h2>
              
              {/* Metadata Form */}
              <div className="space-y-4 mb-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Location (Optional)
                  </label>
                  <input
                    type="text"
                    value={metadata.location}
                    onChange={(e) => setMetadata({...metadata, location: e.target.value})}
                    placeholder="e.g., Production Floor A, Warehouse"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Shift (Optional)
                  </label>
                  <select
                    value={metadata.shift}
                    onChange={(e) => setMetadata({...metadata, shift: e.target.value})}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">Select Shift</option>
                    <option value="Day Shift">Day Shift</option>
                    <option value="Evening Shift">Evening Shift</option>
                    <option value="Night Shift">Night Shift</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Your Name (Optional)
                  </label>
                  <input
                    type="text"
                    value={metadata.associate_name}
                    onChange={(e) => setMetadata({...metadata, associate_name: e.target.value})}
                    placeholder="Enter your name"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Recording Controls */}
              <div className="text-center space-y-4">
                <div className="flex justify-center space-x-4">
                  <button
                    onClick={startRecording}
                    disabled={status === 'recording' || isProcessing}
                    className={`px-8 py-3 rounded-lg font-medium text-white transition-colors ${
                      status === 'recording' || isProcessing
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-red-500 hover:bg-red-600'
                    }`}
                  >
                    {status === 'recording' ? '🔴 Recording...' : '🎙️ Start Recording'}
                  </button>
                  
                  <button
                    onClick={stopRecording}
                    disabled={status !== 'recording'}
                    className={`px-8 py-3 rounded-lg font-medium text-white transition-colors ${
                      status !== 'recording'
                        ? 'bg-gray-400 cursor-not-allowed'
                        : 'bg-blue-500 hover:bg-blue-600'
                    }`}
                  >
                    ⏹️ Stop Recording
                  </button>
                  
                  <button
                    onClick={clearBlobUrl}
                    disabled={!mediaBlobUrl || isProcessing}
                    className="px-6 py-3 bg-gray-500 text-white rounded-lg hover:bg-gray-600 disabled:bg-gray-400 disabled:cursor-not-allowed"
                  >
                    🗑️ Clear
                  </button>
                </div>

                <div className="text-sm text-gray-600">
                  Status: <span className="font-medium">{status}</span>
                </div>
              </div>

              {/* Audio Player */}
              {mediaBlobUrl && (
                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Preview Recording:</h3>
                  <audio src={mediaBlobUrl} controls className="w-full" />
                </div>
              )}

              {/* Processing Status */}
              {isProcessing && (
                <div className="mt-6 p-4 bg-blue-50 rounded-lg text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-2"></div>
                  <p className="text-blue-700 font-medium">Processing your suggestion...</p>
                  <p className="text-blue-600 text-sm">This may take 1-2 minutes</p>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-red-700">{error}</p>
                </div>
              )}

              {/* Result Display */}
              {result && (
                <div className="mt-6 p-6 bg-green-50 border border-green-200 rounded-lg">
                  <h3 className="text-lg font-semibold text-green-800 mb-4">✅ Analysis Complete!</h3>
                  
                  <div className="space-y-3">
                    <div>
                      <span className="font-medium text-gray-700">Summary:</span>
                      <p className="text-gray-600 mt-1">{result.summary}</p>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      <span className="font-medium text-gray-700">Category:</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getCategoryColor(result.lean_category)}`}>
                        {result.lean_category}
                      </span>
                    </div>
                    
                    <div className="flex flex-wrap gap-2">
                      <span className="font-medium text-gray-700">Priority:</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSuggestionLevelColor(result.suggestion_level)}`}>
                        {result.suggestion_level}
                      </span>
                    </div>
                    
                    {result.reasoning && (
                      <div>
                        <span className="font-medium text-gray-700">AI Reasoning:</span>
                        <p className="text-gray-600 text-sm mt-1">{result.reasoning}</p>
                      </div>
                    )}
                  </div>
                  
                  <button
                    onClick={() => setResult(null)}
                    className="mt-4 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                  >
                    Record Another Idea
                  </button>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Suggestions Tracker View */
          <div className="max-w-6xl mx-auto">
            <div className="bg-white rounded-xl shadow-lg p-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-semibold text-gray-800">Kaizen Tracker</h2>
                <button
                  onClick={loadSuggestions}
                  className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
                >
                  🔄 Refresh
                </button>
              </div>

              {suggestions.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-500 text-lg">No suggestions yet. Start recording your ideas!</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {suggestions.map((suggestion) => (
                    <div key={suggestion.id} className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow">
                      <div className="flex justify-between items-start mb-3">
                        <div className="flex flex-wrap gap-2">
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(suggestion.status)}`}>
                            {suggestion.status}
                          </span>
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getCategoryColor(suggestion.lean_category)}`}>
                            {suggestion.lean_category}
                          </span>
                          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getSuggestionLevelColor(suggestion.suggestion_level)}`}>
                            {suggestion.suggestion_level}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">
                          {new Date(suggestion.timestamp).toLocaleDateString()} {new Date(suggestion.timestamp).toLocaleTimeString()}
                        </div>
                      </div>
                      
                      <h3 className="font-semibold text-gray-800 mb-2">{suggestion.summary}</h3>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600 mb-3">
                        <div><strong>Location:</strong> {suggestion.location || 'Not specified'}</div>
                        <div><strong>Shift:</strong> {suggestion.shift || 'Not specified'}</div>
                        <div><strong>Associate:</strong> {suggestion.associate_name || 'Anonymous'}</div>
                      </div>
                      
                      {suggestion.reasoning && (
                        <p className="text-sm text-gray-600 mb-3">
                          <strong>AI Analysis:</strong> {suggestion.reasoning}
                        </p>
                      )}
                      
                      {suggestion.status === 'pending_review' && (
                        <div className="flex gap-2 mt-4">
                          <button
                            onClick={() => updateSuggestionStatus(suggestion.id, 'approved')}
                            className="px-4 py-2 bg-green-500 text-white text-sm rounded hover:bg-green-600"
                          >
                            ✅ Approve
                          </button>
                          <button
                            onClick={() => updateSuggestionStatus(suggestion.id, 'rejected')}
                            className="px-4 py-2 bg-red-500 text-white text-sm rounded hover:bg-red-600"
                          >
                            ❌ Reject
                          </button>
                        </div>
                      )}
                      
                      {suggestion.status === 'approved' && (
                        <button
                          onClick={() => updateSuggestionStatus(suggestion.id, 'implemented')}
                          className="px-4 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 mt-4"
                        >
                          ✅ Mark as Implemented
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;