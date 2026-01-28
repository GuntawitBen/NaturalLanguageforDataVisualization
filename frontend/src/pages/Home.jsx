import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { API_ENDPOINTS } from '../config';
import {
  Database,
  Calendar,
  FileText,
  Trash2,
  Eye,
  BarChart3,
  Upload,
  Layers,
  ArrowUpRight,
  Sparkles,
  Grid3X3,
  ChevronRight
} from 'lucide-react';
import './Home.css';

// GameCube-style 3D Cube Animation
function CubeAnimation() {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let animationId;
    let time = 0;

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio;
      canvas.height = canvas.offsetHeight * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };

    // 3D projection
    const project = (x, y, z, cx, cy, scale) => {
      const perspective = 400;
      const factor = perspective / (perspective + z);
      return {
        x: cx + x * factor * scale,
        y: cy + y * factor * scale,
        scale: factor
      };
    };

    // Rotate point around axis
    const rotateY = (x, y, z, angle) => {
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      return {
        x: x * cos - z * sin,
        y: y,
        z: x * sin + z * cos
      };
    };

    const rotateX = (x, y, z, angle) => {
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      return {
        x: x,
        y: y * cos - z * sin,
        z: y * sin + z * cos
      };
    };

    // Draw a single cube face
    const drawFace = (points, color, opacity) => {
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i++) {
        ctx.lineTo(points[i].x, points[i].y);
      }
      ctx.closePath();
      ctx.fillStyle = color.replace(')', `, ${opacity})`).replace('rgb', 'rgba');
      ctx.fill();
      ctx.strokeStyle = `rgba(251, 191, 36, ${opacity * 0.5})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    };

    // Draw cube
    const drawCube = (cx, cy, size, rotX, rotY, offset, colorType) => {
      const half = size / 2;

      // Cube vertices
      let vertices = [
        { x: -half, y: -half, z: -half },
        { x: half, y: -half, z: -half },
        { x: half, y: half, z: -half },
        { x: -half, y: half, z: -half },
        { x: -half, y: -half, z: half },
        { x: half, y: -half, z: half },
        { x: half, y: half, z: half },
        { x: -half, y: half, z: half },
      ];

      // Apply rotations
      vertices = vertices.map(v => {
        let r = rotateY(v.x, v.y, v.z, rotY);
        r = rotateX(r.x, r.y, r.z, rotX);
        return r;
      });

      // Project to 2D
      const projected = vertices.map(v =>
        project(v.x, v.y, v.z + offset, cx, cy, 1)
      );

      // Define faces with their average z for sorting
      const faces = [
        { indices: [0, 1, 2, 3], z: (vertices[0].z + vertices[1].z + vertices[2].z + vertices[3].z) / 4, color: colorType === 'yellow' ? 'rgb(251, 191, 36)' : 'rgb(239, 68, 68)', shade: 0.7 },
        { indices: [4, 5, 6, 7], z: (vertices[4].z + vertices[5].z + vertices[6].z + vertices[7].z) / 4, color: colorType === 'yellow' ? 'rgb(251, 191, 36)' : 'rgb(239, 68, 68)', shade: 1 },
        { indices: [0, 1, 5, 4], z: (vertices[0].z + vertices[1].z + vertices[5].z + vertices[4].z) / 4, color: colorType === 'yellow' ? 'rgb(200, 150, 20)' : 'rgb(200, 50, 50)', shade: 0.85 },
        { indices: [2, 3, 7, 6], z: (vertices[2].z + vertices[3].z + vertices[7].z + vertices[6].z) / 4, color: colorType === 'yellow' ? 'rgb(200, 150, 20)' : 'rgb(200, 50, 50)', shade: 0.85 },
        { indices: [0, 3, 7, 4], z: (vertices[0].z + vertices[3].z + vertices[7].z + vertices[4].z) / 4, color: colorType === 'yellow' ? 'rgb(180, 130, 10)' : 'rgb(180, 40, 40)', shade: 0.6 },
        { indices: [1, 2, 6, 5], z: (vertices[1].z + vertices[2].z + vertices[6].z + vertices[5].z) / 4, color: colorType === 'yellow' ? 'rgb(255, 210, 60)' : 'rgb(255, 100, 100)', shade: 0.95 },
      ];

      // Sort faces by z (back to front)
      faces.sort((a, b) => a.z - b.z);

      // Draw faces
      faces.forEach(face => {
        const points = face.indices.map(i => projected[i]);
        drawFace(points, face.color, face.shade);
      });
    };

    const animate = () => {
      time += 0.015;
      const width = canvas.offsetWidth;
      const height = canvas.offsetHeight;

      ctx.clearRect(0, 0, width, height);

      const centerX = width / 2;
      const centerY = height / 2;

      // Main rotating cube
      drawCube(
        centerX,
        centerY,
        60,
        time * 0.8,
        time,
        0,
        'yellow'
      );

      // Orbiting smaller cubes
      for (let i = 0; i < 4; i++) {
        const angle = time * 0.5 + (i * Math.PI / 2);
        const orbitRadius = 100;
        const ox = Math.cos(angle) * orbitRadius;
        const oy = Math.sin(angle * 0.7) * 30;
        const oz = Math.sin(angle) * orbitRadius;

        drawCube(
          centerX + ox,
          centerY + oy,
          25,
          time * 1.2 + i,
          -time * 0.9 + i,
          oz,
          i % 2 === 0 ? 'yellow' : 'red'
        );
      }

      // Tiny floating cubes
      for (let i = 0; i < 6; i++) {
        const angle = time * 0.3 + (i * Math.PI / 3);
        const radius = 140 + Math.sin(time + i) * 20;
        const ox = Math.cos(angle) * radius;
        const oy = Math.sin(angle * 0.5 + i) * 50;
        const oz = Math.sin(angle) * radius * 0.5;

        drawCube(
          centerX + ox,
          centerY + oy,
          12,
          time * 2 + i * 2,
          time * 1.5 + i,
          oz + 50,
          'yellow'
        );
      }

      animationId = requestAnimationFrame(animate);
    };

    resize();
    animate();

    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return <canvas ref={canvasRef} className="cube-canvas" />;
}

export default function Home() {
  const { user, sessionToken, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [greeting, setGreeting] = useState('');

  useEffect(() => {
    const getGreeting = () => {
      const hour = new Date().getHours();
      if (hour < 12) return 'Good morning';
      if (hour < 17) return 'Good afternoon';
      return 'Good evening';
    };
    setGreeting(getGreeting());
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchDatasets();
  }, [isAuthenticated, navigate]);

  const fetchDatasets = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.LIST, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) throw new Error('Failed to fetch datasets');
      const data = await response.json();
      setDatasets(data);
    } catch (err) {
      console.error('Error fetching datasets:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (datasetId, datasetName) => {
    if (!window.confirm(`Delete "${datasetName}"?`)) return;

    try {
      const response = await fetch(API_ENDPOINTS.DATASETS.DELETE(datasetId), {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${sessionToken}` },
      });

      if (!response.ok) throw new Error('Failed to delete dataset');
      fetchDatasets();
    } catch (err) {
      console.error('Error deleting dataset:', err);
      alert('Failed to delete dataset');
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  const totalRows = datasets.reduce((sum, ds) => sum + ds.row_count, 0);
  const totalSize = datasets.reduce((sum, ds) => sum + ds.file_size_bytes, 0);

  if (loading) {
    return (
      <div className="home-page">
        <div className="loading-state">
          <div className="loading-terminal">
            <div className="terminal-header">
              <span className="terminal-dot red"></span>
              <span className="terminal-dot yellow"></span>
              <span className="terminal-dot green"></span>
              <span className="terminal-title">dashboard_init.exe</span>
            </div>
            <div className="terminal-body">
              <div className="terminal-line">
                <span className="prompt">$</span>
                <span className="command">initializing dashboard...</span>
                <span className="cursor"></span>
              </div>
              <div className="loading-bar">
                <div className="loading-progress"></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="hero-content">
          <p className="hero-greeting">{greeting}</p>
          <h1 className="hero-title">
            {user?.name?.split(' ')[0] || 'User'}
            <span className="accent">.</span>
          </h1>
          <p className="hero-description">
            Transform data into insights with natural language
          </p>
          <button className="hero-cta" onClick={() => navigate('/data-cleaning')}>
            <Upload size={16} />
            <span>Upload dataset</span>
            <ChevronRight size={16} className="cta-chevron" />
          </button>
        </div>

        {/* GameCube-style Animation */}
        <div className="hero-animation">
          <CubeAnimation />
        </div>
      </section>

      {/* Stats Bar */}
      <section className="stats-bar">
        <div className="stat-item">
          <span className="stat-value">{datasets.length}</span>
          <span className="stat-label">datasets</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <span className="stat-value">{totalRows.toLocaleString()}</span>
          <span className="stat-label">rows</span>
        </div>
        <div className="stat-divider"></div>
        <div className="stat-item">
          <span className="stat-value">{formatFileSize(totalSize)}</span>
          <span className="stat-label">storage</span>
        </div>
      </section>

      {/* Datasets Section */}
      <section className="datasets-section">
        <div className="section-header">
          <div className="section-title">
            <Grid3X3 size={16} />
            <h2>Recent Datasets</h2>
          </div>
          {datasets.length > 0 && (
            <button className="text-button" onClick={() => navigate('/datasets')}>
              View all
              <ArrowUpRight size={14} />
            </button>
          )}
        </div>

        {datasets.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">
              <Database size={32} />
            </div>
            <h3>No datasets yet</h3>
            <p>Upload your first CSV file to get started</p>
            <button className="empty-cta" onClick={() => navigate('/data-cleaning')}>
              <Sparkles size={16} />
              <span>Get started</span>
            </button>
          </div>
        ) : (
          <div className="datasets-grid">
            {datasets.slice(0, 6).map((dataset, index) => (
              <article key={dataset.dataset_id} className="dataset-card" style={{ '--delay': `${index * 50}ms` }}>
                <div className="card-header">
                  <div className="card-icon">
                    <FileText size={18} />
                  </div>
                  <div className="card-meta">
                    <h3 className="card-title">{dataset.dataset_name}</h3>
                    <span className="card-filename">{dataset.original_filename}</span>
                  </div>
                </div>

                <div className="card-stats">
                  <div className="card-stat">
                    <BarChart3 size={12} />
                    <span>{dataset.row_count.toLocaleString()} rows</span>
                  </div>
                  <div className="card-stat">
                    <Layers size={12} />
                    <span>{dataset.column_count} cols</span>
                  </div>
                  <div className="card-stat">
                    <Calendar size={12} />
                    <span>{formatDate(dataset.upload_date)}</span>
                  </div>
                  <div className="card-stat">
                    <Database size={12} />
                    <span>{formatFileSize(dataset.file_size_bytes)}</span>
                  </div>
                </div>

                <div className="card-actions">
                  <button
                    className="card-btn primary"
                    onClick={() => navigate(`/datasets/${dataset.dataset_id}`)}
                  >
                    <Eye size={14} />
                    <span>Explore</span>
                  </button>
                  <button
                    className="card-btn danger"
                    onClick={() => handleDelete(dataset.dataset_id, dataset.dataset_name)}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
