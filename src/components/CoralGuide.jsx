import React, { useState } from 'react';
import coralData from '../data/caribbean-corals.json';
import './CoralGuide.css';

// Placeholder images from iNaturalist - will be replaced with local photos later
const CORAL_IMAGES = {
  'elkhorn': 'https://inaturalist-open-data.s3.amazonaws.com/photos/387555070/medium.jpeg',
  'staghorn': 'https://inaturalist-open-data.s3.amazonaws.com/photos/262267058/medium.jpeg',
  'mustard-hill': 'https://inaturalist-open-data.s3.amazonaws.com/photos/116660486/medium.jpeg',
  'lettuce': 'https://inaturalist-open-data.s3.amazonaws.com/photos/128231860/medium.jpg',
  
  // FIXED: Massive starlet was showing S. radians (lesser starlet)
  // Now uses photo 138509 which is actual S. siderea (was incorrectly on brain)
  'massive-starlet': 'https://inaturalist-open-data.s3.amazonaws.com/photos/138509/medium.jpg',
  
  // FIXED: Brain coral was showing Siderastrea siderea (star coral)
  // Now uses grooved brain photo 387920934
  'brain': 'https://inaturalist-open-data.s3.amazonaws.com/photos/387920934/medium.jpeg',
  
  'boulder-brain': 'https://inaturalist-open-data.s3.amazonaws.com/photos/138509/medium.jpg',
  'mountainous-star': 'https://inaturalist-open-data.s3.amazonaws.com/photos/48931058/medium.jpeg',
  'lobed-star': 'https://inaturalist-open-data.s3.amazonaws.com/photos/62956167/medium.jpeg',
  'boulder-star': 'https://inaturalist-open-data.s3.amazonaws.com/photos/241739162/medium.jpeg',
  'great-star': 'https://inaturalist-open-data.s3.amazonaws.com/photos/67783121/medium.jpg',
  'symmetrical-brain': 'https://inaturalist-open-data.s3.amazonaws.com/photos/391316735/medium.jpeg',
  'grooved-brain': 'https://inaturalist-open-data.s3.amazonaws.com/photos/387920934/medium.jpeg',
  'finger': 'https://inaturalist-open-data.s3.amazonaws.com/photos/62956167/medium.jpeg',
  'lesser-starlet': 'https://inaturalist-open-data.s3.amazonaws.com/photos/138473/medium.jpg',
  
  // FIXED: These two were swapped
  // Smooth flower now has photo 138471 (was on blushing-star)
  'smooth-flower': 'https://inaturalist-open-data.s3.amazonaws.com/photos/138471/medium.jpg',
  
  'pillar': 'https://inaturalist-open-data.s3.amazonaws.com/photos/46127214/medium.jpeg',
  'elliptical-star': 'https://inaturalist-open-data.s3.amazonaws.com/photos/138487/medium.jpg',
  
  // FIXED: Blushing star now has photo 138470 (was on smooth-flower)
  'blushing-star': 'https://inaturalist-open-data.s3.amazonaws.com/photos/138470/medium.jpg'
};

function CoralGuide() {
  const [selectedCoral, setSelectedCoral] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const getStatusColor = (status) => {
    const colors = {
      'CR': '#d32f2f', // Critically Endangered - red
      'EN': '#f57c00', // Endangered - orange
      'VU': '#fbc02d', // Vulnerable - yellow
      'NT': '#7cb342', // Near Threatened - light green
      'LC': '#388e3c'  // Least Concern - green
    };
    return colors[status] || '#757575';
  };

  const filteredCorals = coralData.filter(coral =>
    coral.commonName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    coral.scientificName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <>
      <div className="coral-guide-section">
        <div className="coral-guide-header">
          <h3>🪸 Learn About Caribbean Corals</h3>
          <p>Common species found in USVI waters</p>
        </div>

        {/* Search Bar */}
        <div className="coral-search">
          <input
            type="text"
            placeholder="Search coral species..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="search-input"
          />
        </div>

        {/* Scrollable Coral Gallery */}
        <div className="coral-carousel">
          {filteredCorals.map(coral => (
            <div 
              key={coral.id} 
              className="coral-card-home"
              onClick={() => setSelectedCoral(coral)}
            >
              <div className="coral-image-container">
                <img 
                  src={CORAL_IMAGES[coral.id]} 
                  alt={coral.commonName}
                  className="coral-image"
                />
                <span 
                  className="status-badge-overlay"
                  style={{ backgroundColor: getStatusColor(coral.iucnStatus) }}
                >
                  {coral.iucnStatus}
                </span>
              </div>
              <div className="coral-info">
                <h4>{coral.commonName}</h4>
                <p className="scientific-name-home">{coral.scientificName}</p>
              </div>
            </div>
          ))}
        </div>

        {filteredCorals.length === 0 && (
          <p className="no-results">No corals found matching "{searchTerm}"</p>
        )}
      </div>

      {/* Detail Modal */}
      {selectedCoral && (
        <CoralDetailModal 
          coral={selectedCoral}
          onClose={() => setSelectedCoral(null)}
          getStatusColor={getStatusColor}
          imageUrl={CORAL_IMAGES[selectedCoral.id]}
        />
      )}
    </>
  );
}

function CoralDetailModal({ coral, onClose, getStatusColor, imageUrl }) {
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content-coral" onClick={(e) => e.stopPropagation()}>
        <button className="close-button" onClick={onClose}>×</button>
        
        {/* Large Hero Image */}
        <div className="modal-image-hero">
          <img src={imageUrl} alt={coral.commonName} />
          <span 
            className="status-badge-large"
            style={{ backgroundColor: getStatusColor(coral.iucnStatus) }}
          >
            {coral.conservationStatus}
          </span>
        </div>

        <div className="modal-header">
          <h2>{coral.commonName}</h2>
          <p className="scientific-name-large">{coral.scientificName}</p>
          <p className="family-name">{coral.family}</p>
        </div>

        <div className="modal-body">
          <section>
            <h3>Description</h3>
            <p>{coral.description}</p>
          </section>

          <section>
            <h3>Habitat & Depth</h3>
            <p>{coral.habitat}</p>
            <div className="quick-stat">
              <strong>Depth Range:</strong> {coral.depthRange}
            </div>
          </section>

          <section>
            <h3>How to Identify</h3>
            <ul className="id-tips">
              {coral.identificationTips.map((tip, index) => (
                <li key={index}>{tip}</li>
              ))}
            </ul>
          </section>

          <div className="coral-specs-grid">
            <div className="spec-box">
              <div className="spec-label">Max Colony Size</div>
              <div className="spec-value">{coral.maxColonySize}</div>
            </div>
            <div className="spec-box">
              <div className="spec-label">Conservation Status</div>
              <div className="spec-value">{coral.conservationStatus}</div>
            </div>
          </div>

          {coral.usviNotes && (
            <section>
              <h3>USVI Status</h3>
              <div className="usvi-note">
                {coral.usviNotes}
              </div>
            </section>
          )}

          {coral.threatFactors && coral.threatFactors.length > 0 && (
            <section>
              <h3>Threat Factors</h3>
              <div className="threat-tags">
                {coral.threatFactors.map((threat, index) => (
                  <span key={index} className="threat-tag">{threat}</span>
                ))}
              </div>
            </section>
          )}

          <div className="modal-footer-note">
            {coral.photoAttribution && (
              <p className="photo-credit">
                Photo by <a href={coral.photoAttribution.sourceUrl} target="_blank" rel="noopener noreferrer">{coral.photoAttribution.photographer}</a> • {coral.photoAttribution.license}
              </p>
            )}
            <p className="inaturalist-link">
              From <a href="https://www.inaturalist.org/guides/19437" target="_blank" rel="noopener noreferrer">iNaturalist Caribbean Coral Guide</a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default CoralGuide;
