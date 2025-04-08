import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import './App.css';

// Configure axios defaults
axios.defaults.baseURL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

// Custom modal component for displaying results
const ResultModal = ({ isOpen, onClose, results }) => {
  if (!isOpen) return null;
  
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h3>Upload Results</h3>
        <div className="results-summary">
          <div className="result-item success">
            <span className="result-count">{results.success}</span>
            <span className="result-label">Successful</span>
          </div>
          {results.skipped > 0 && (
            <div className="result-item warning">
              <span className="result-count">{results.skipped}</span>
              <span className="result-label">Skipped</span>
            </div>
          )}
          {results.failed > 0 && (
            <div className="result-item error">
              <span className="result-count">{results.failed}</span>
              <span className="result-label">Failed</span>
            </div>
          )}
        </div>
        
        {results.skippedFiles.length > 0 && (
          <div className="skipped-files">
            <h4>Skipped Files (missing contact info or duplicates):</h4>
            <ul>
              {results.skippedFiles.map((file, index) => (
                <li key={index}>{file}</li>
              ))}
            </ul>
          </div>
        )}
        
        <button className="modal-close" onClick={onClose}>Close</button>
      </div>
    </div>
  );
};

// Top Resumes Page Component
const TopResumesPage = () => {
  const [topResumes, setTopResumes] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [limit, setLimit] = useState(10);
  const [selectedJobId, setSelectedJobId] = useState('all');
  const [availableJobs, setAvailableJobs] = useState([]);
  const limitOptions = [10, 20, 30, 50, 100];

  useEffect(() => {
    fetchJobs();
    fetchTopResumes();
  }, [limit, selectedJobId]);

  const fetchJobs = async () => {
    try {
      const response = await axios.get('/api/jobs');
      setAvailableJobs(response.data.jobs);
    } catch (err) {
      console.error("Failed to fetch jobs for filter:", err);
    }
  };

  const fetchTopResumes = async () => {
    try {
      setLoading(true);
      let url = `/api/top-resumes?limit=${limit}`;
      if (selectedJobId !== 'all') {
        url += `&job_id=${selectedJobId}`;
      }
      const response = await axios.get(url);
      setTopResumes(response.data.top_resumes);
      setError('');
    } catch (err) {
      setError('Failed to fetch top resumes');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const viewResume = (resumePath) => {
    const resumeUrl = `${axios.defaults.baseURL}/api/resumes/${resumePath}`;
    window.open(resumeUrl, '_blank');
  };

  const downloadResume = (resumePath) => {
    const downloadUrl = `${axios.defaults.baseURL}/api/resumes/${resumePath}?download=true`;
    window.open(downloadUrl, '_blank');
  };

  return (
    <div className="top-resumes-page">
      <h2>Top Resumes</h2>
      
      <div className="filter-controls">
        <div className="job-filter">
          <label>Filter by Job: </label>
          <select 
            value={selectedJobId} 
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="job-selector"
          >
            <option value="all">All Jobs</option>
            {availableJobs.map(job => (
              <option key={job.id} value={job.id}>
                {job.title}
              </option>
            ))}
          </select>
        </div>
        
        <div className="limit-selector">
          <label>Show top: </label>
          <select 
            value={limit} 
            onChange={(e) => setLimit(Number(e.target.value))}
          >
            {limitOptions.map(option => (
              <option key={option} value={option}>
                {option} Resumes
              </option>
            ))}
          </select>
        </div>
      </div>
      
      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading...</div>}
      
      {topResumes.length > 0 ? (
        <div className="top-resumes-list">
          {topResumes.map((resume, index) => (
            <div key={resume.id} className="top-resume-item">
              <div className="resume-rank">{index + 1}</div>
              <div className="resume-content">
                <h3>{resume.name || `Candidate ${resume.candidate_id.substring(0, 8)}`}</h3>
                <p className="job-title">Job: {resume.job_title}</p>
                {resume.email && <p>Email: {resume.email}</p>}
                {resume.mobile && <p>Mobile: {resume.mobile}</p>}
                {resume.city && <p>City: {resume.city}</p>}
                <p className="score">Score: {resume.score.toFixed(2)}%</p>
                
                <div className="resume-actions">
                  <button 
                    className="view-resume-btn"
                    onClick={() => viewResume(resume.resume_path)}
                  >
                    View Resume
                  </button>
                  <button 
                    className="download-resume-btn"
                    onClick={() => downloadResume(resume.resume_path)}
                  >
                    Download
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="no-resumes">
          <p>No resumes found. Add candidates to jobs to see top resumes here.</p>
        </div>
      )}
    </div>
  );
};

function App() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [newJob, setNewJob] = useState({ title: '', description: '' });
  const [candidateInfo, setCandidateInfo] = useState({ name: '', email: '', mobile: '', city: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [showCandidateForm, setShowCandidateForm] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [uploadResults, setUploadResults] = useState({ success: 0, skipped: 0, failed: 0, skippedFiles: [] });
  const [activePage, setActivePage] = useState('jobs'); // 'jobs' or 'top-resumes'
  const fileInputRef = useRef(null);

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/jobs');
      setJobs(response.data.jobs);
      setError('');
    } catch (err) {
      setError('Failed to fetch jobs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const createJob = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const response = await axios.post('/api/jobs', newJob);
      setNewJob({ title: '', description: '' });
      fetchJobs();
      setError('');
    } catch (err) {
      const errorMessage = err.response?.data?.error || 'Failed to create job';
      setError(`Error: ${errorMessage}`);
      console.error('Error creating job:', err.response?.data || err);
    } finally {
      setLoading(false);
    }
  };

  const deleteJob = async (jobId) => {
    if (!window.confirm('Are you sure you want to delete this job? This will also delete all associated candidates.')) {
      return;
    }
    
    try {
      setLoading(true);
      await axios.delete(`/api/jobs/${jobId}`);
      
      // If we're deleting the selected job, clear the selection
      if (selectedJob && selectedJob.id === jobId) {
        setSelectedJob(null);
        setCandidates([]);
      }
      
      // Refresh the jobs list
      fetchJobs();
      setError('');
    } catch (err) {
      const errorMessage = err.response?.data?.error || 'Failed to delete job';
      setError(`Error: ${errorMessage}`);
      console.error('Error deleting job:', err.response?.data || err);
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFiles(e.target.files);
    }
  };

  const handleFiles = (files) => {
    if (!selectedJob) return;
    
    const newFiles = Array.from(files);
    setSelectedFiles(prevFiles => [...prevFiles, ...newFiles]);
    setShowCandidateForm(true);
  };

  const removeFile = (index) => {
    setSelectedFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
    if (selectedFiles.length <= 1) {
      setShowCandidateForm(false);
    }
  };

  const handleCandidateSubmit = async (e) => {
    e.preventDefault();
    if (!selectedJob || selectedFiles.length === 0) return;

    try {
      setLoading(true);
      
      const results = {
        success: 0,
        skipped: 0,
        failed: 0,
        skippedFiles: []
      };
      
      const uploadPromises = selectedFiles.map(async (file, index) => {
        const formData = new FormData();
        formData.append('file', file);
        
        // Only include manual info if uploading a single resume
        if (selectedFiles.length === 1) {
          formData.append('name', candidateInfo.name);
          formData.append('email', candidateInfo.email);
          formData.append('mobile', candidateInfo.mobile);
          formData.append('city', candidateInfo.city);
        }
        
        try {
          await axios.post(`/api/jobs/${selectedJob.id}/upload-resume`, formData);
          results.success++;
          return { status: 'success', file };
        } catch (err) {
          if (err.response && err.response.status === 400 && 
              err.response.data.error && 
              err.response.data.error.includes('No email or mobile number found')) {
            results.skipped++;
            results.skippedFiles.push(file.name);
            return { status: 'skipped', file, reason: 'No email or mobile number found' };
          } else if (err.response && err.response.status === 409) {
            results.skipped++;
            results.skippedFiles.push(file.name);
            return { status: 'skipped', file, reason: 'Duplicate candidate' };
          } else {
            results.failed++;
            return { status: 'failed', file, error: err };
          }
        }
      });

      await Promise.all(uploadPromises);
      fetchCandidates(selectedJob.id);
      
      setError('');
      setCandidateInfo({ name: '', email: '', mobile: '', city: '' });
      setShowCandidateForm(false);
      setSelectedFiles([]);
      
      // Show results in modal instead of alert
      setUploadResults(results);
      setModalOpen(true);
    } catch (err) {
      if (err.response && err.response.status === 409) {
        setError('One or more candidates have already been submitted for this job.');
      } else {
        setError('Failed to upload resumes: ' + (err.response?.data?.error || 'Unknown error'));
      }
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCandidates = async (jobId) => {
    try {
      setLoading(true);
      const response = await axios.get(`/api/jobs/${jobId}/candidates`);
      setCandidates(response.data.candidates);
      setError('');
    } catch (err) {
      setError('Failed to fetch candidates');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const selectJob = (job) => {
    setSelectedJob(job);
    fetchCandidates(job.id);
    setShowCandidateForm(false);
    setSelectedFiles([]);
  };

  const onButtonClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div className="App">
      <div className="app-header">
        <h1><span className="logo-icon">RS</span> Resume Shortlister</h1>
        <p className="tagline">Visionary VPA AI Talent Screening</p>
        
        <nav className="app-nav">
          <button 
            className={`nav-link ${activePage === 'jobs' ? 'active' : ''}`} 
            onClick={() => setActivePage('jobs')}
          >
            Jobs
          </button>
          <button 
            className={`nav-link ${activePage === 'top-resumes' ? 'active' : ''}`} 
            onClick={() => setActivePage('top-resumes')}
          >
            Top Resumes
          </button>
        </nav>
      </div>
      
      {error && <div className="error">{error}</div>}
      {loading && <div className="loading">Loading...</div>}

      {activePage === 'jobs' ? (
        <>
          <div className="job-form">
            <h2>Create New Job</h2>
            <form onSubmit={createJob}>
              <input
                type="text"
                placeholder="Job Title"
                value={newJob.title}
                onChange={(e) => setNewJob({ ...newJob, title: e.target.value })}
                required
              />
              <textarea
                placeholder="Job Description"
                value={newJob.description}
                onChange={(e) => setNewJob({ ...newJob, description: e.target.value })}
                required
              />
              <button type="submit" disabled={loading}>Create Job</button>
            </form>
          </div>

          <div className="content">
            <div className="jobs-list">
              <h2>Jobs</h2>
              {jobs.map(job => (
                <div
                  key={job.id}
                  className={`job-item ${selectedJob?.id === job.id ? 'selected' : ''}`}
                >
                  <div className="job-content" onClick={() => selectJob(job)}>
                    <h3>{job.title}</h3>
                    <p>{job.description}</p>
                  </div>
                  <button 
                    className="delete-job-btn" 
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteJob(job.id);
                    }}
                    title="Delete job"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>

            {selectedJob && (
              <div className="candidates-list">
                <h2>Candidates for {selectedJob.title}</h2>
                
                {!showCandidateForm ? (
                  <div 
                    className={`file-drop-zone ${dragActive ? 'active' : ''}`}
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    onClick={onButtonClick}
                  >
                    <div className="icon">📄</div>
                    <p>Drag and drop your resumes here or click to select files</p>
                    <p>You can upload multiple resumes at once</p>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept=".pdf,.docx"
                      onChange={handleFileSelect}
                      style={{ display: 'none' }}
                      multiple
                    />
                  </div>
                ) : (
                  <form onSubmit={handleCandidateSubmit} className={selectedFiles.length > 1 ? "multi-file-upload" : ""}>
                    <h3>Selected Resumes {selectedFiles.length > 0 && `(${selectedFiles.length})`}</h3>
                    <div className="selected-files">
                      {selectedFiles.map((file, index) => (
                        <div key={index} className="file-item">
                          <span className="file-name">{file.name}</span>
                          <button 
                            type="button" 
                            className="remove-file" 
                            onClick={() => removeFile(index)}
                          >
                            ×
                          </button>
                        </div>
                      ))}
                    </div>
                    {selectedFiles.length > 1 ? (
                      <p className="info-note">Information will be automatically extracted from each resume.</p>
                    ) : (
                      <>
                        <p className="info-note">These details will be applied to the selected resume. Leave blank if you want information extracted automatically.</p>
                        <input
                          type="text"
                          placeholder="Name (optional)"
                          value={candidateInfo.name}
                          onChange={(e) => setCandidateInfo({ ...candidateInfo, name: e.target.value })}
                        />
                        <input
                          type="email"
                          placeholder="Email (optional)"
                          value={candidateInfo.email}
                          onChange={(e) => setCandidateInfo({ ...candidateInfo, email: e.target.value })}
                        />
                        <input
                          type="text"
                          placeholder="Mobile Number (optional)"
                          value={candidateInfo.mobile}
                          onChange={(e) => setCandidateInfo({ ...candidateInfo, mobile: e.target.value })}
                        />
                        <input
                          type="text"
                          placeholder="City (optional)"
                          value={candidateInfo.city}
                          onChange={(e) => setCandidateInfo({ ...candidateInfo, city: e.target.value })}
                        />
                      </>
                    )}
                    <div className="button-container">
                      <button type="submit" disabled={loading}>Upload {selectedFiles.length} Resume{selectedFiles.length !== 1 && 's'}</button>
                      <button 
                        type="button" 
                        onClick={() => {
                          setShowCandidateForm(false);
                          setSelectedFiles([]);
                        }}
                        disabled={loading}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                )}
                
                {candidates.length > 0 ? (
                  <>
                    <h3>Results ({candidates.length} candidate{candidates.length !== 1 && 's'})</h3>
                    {candidates.map(candidate => (
                      <div key={candidate.id} className="candidate-item">
                        <h3>{candidate.name || `Candidate ${candidate.candidate_id.substring(0, 8)}`}</h3>
                        {candidate.email && <p>Email: {candidate.email}</p>}
                        {candidate.mobile && <p>Mobile: {candidate.mobile}</p>}
                        {candidate.city && <p>City: {candidate.city}</p>}
                        <p className="score">Score: {candidate.score.toFixed(2)}%</p>
                      </div>
                    ))}
                  </>
                ) : (
                  !showCandidateForm && (
                    <div className="no-candidates">
                      <p>No candidates found for this job. Upload resumes to see results here.</p>
                    </div>
                  )
                )}
              </div>
            )}
          </div>
        </>
      ) : (
        <TopResumesPage />
      )}
      
      <footer className="app-footer">
        <p>&copy; {new Date().getFullYear()} Visionary VPA Resume Shortlister. All rights reserved.</p>
        <p>Powered by Visionary VPA </p>
      </footer>
      
      {/* Results Modal */}
      <ResultModal 
        isOpen={modalOpen} 
        onClose={() => setModalOpen(false)} 
        results={uploadResults} 
      />
    </div>
  );
}

export default App;