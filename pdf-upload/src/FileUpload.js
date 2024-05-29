import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import './upload.css'

function FileUpload({ setUploadComplete }) {
  const [files, setFiles] = useState([]);
  const [message, setMessage] = useState('');
  const navigate = useNavigate();

  const onFileChange = (event) => {
    setFiles(Array.from(event.target.files));
  };

  const onFileUpload = async () => {
    if (files.length === 0) {
      setMessage('Please select files to upload');
      return;
    }

    const formData = new FormData();
    files.forEach((file) => formData.append('files', file));

    try {
      const response = await axios.post('http://localhost:5000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setMessage(response.data.message);
      setUploadComplete(true);
      navigate('/chat');
    } catch (error) {
      setMessage(error.response ? error.response.data.error : 'An error occurred');
      setUploadComplete(false);
    }
  };

  return (
    <div className="FileUpload-background">
      <div className="navbar">
        <div className="logo">PDFChat</div>
        <div className="profile-symbol">Profile</div>
      </div>
      <div className="FileUpload">
        <h1>Upload PDF Documents</h1>
        <input type="file" onChange={onFileChange} accept="application/pdf" multiple />
        <button onClick={onFileUpload}>Upload</button>
        <p>{message}</p>
      </div>
    </div>
  );
}

export default FileUpload;
