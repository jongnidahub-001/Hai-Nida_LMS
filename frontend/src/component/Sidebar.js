import React, { useState } from 'react';
import logo from '../logo.svg';
import dev1 from '../assets/dev1.jpg';

function Sidebar({ collapsed, onToggle }) {
  return (
    <aside
      className="has-background-white-ter"
      style={{
        minHeight: '100vh',
        width: collapsed ? '60px' : '260px',
        borderRight: '1px solid #eee',
        padding: collapsed ? '1.5rem 0.2rem' : '1.5rem 0.5rem',
        transition: 'width 0.2s',
        overflow: 'hidden',
        position: 'relative',
        backgroundColor: '#f5f5f5 !important',
        color: '#363636 !important',
      }}
    >
      <button
        className="delete is-pulled-right"
        style={{ 
          margin: '0.5rem 1rem 0 0', 
          position: 'absolute', 
          right: 0, 
          top: 0, 
          zIndex: 2,
          backgroundColor: 'transparent',
          color: '#363636 !important'
        }}
        aria-label="toggle sidebar"
        onClick={onToggle}
      >
        {collapsed ? <span style={{ fontWeight: 'bold', fontSize: '1.5rem', color: '#363636' }}>&#9776;</span> : '×'}
      </button>
      {!collapsed && (
        <div className="has-text-centered" style={{ marginTop: '2.5rem', color: '#363636 !important' }}>
          <img src={dev1} alt="dev1" style={{ width: '70px', borderRadius: '50%' }} />
          <div className="mt-2 mb-4">
            <div className="has-text-weight-bold is-size-6" style={{ color: '#363636 !important' }}>รศ.ดร. จงสวัสดิ์ จงวัฒน์ผล</div>
            <div className="is-size-7" style={{ color: '#4a4a4a !important' }}>คณะบริหารธุรกิจ<br />สถาบันบัณฑิตพัฒนบริหารศาสตร์</div>
          </div>
          <img src={dev1} alt="dev2" style={{ width: '70px', borderRadius: '50%' }} />
          <div className="mt-2 mb-4">
            <div className="has-text-weight-bold is-size-7" style={{ color: '#363636 !important' }}>ฐณพงศ์ จันทนะสุคนธ์<br /><span className='has-text-weight-normal' style={{ color: '#4a4a4a !important' }}>Professional MBA #15<br />GenAI Developer</span></div>
          </div>
          <img src={dev1} alt="dev3" style={{ width: '70px', borderRadius: '50%' }} />
          <div className="mt-2">
            <div className="has-text-weight-bold is-size-7" style={{ color: '#363636 !important' }}>คณิกร กาญจนวงศ์<br /><span className='has-text-weight-normal' style={{ color: '#4a4a4a !important' }}>Professional MBA #15<br />UX/UI Designer</span></div>
          </div>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
