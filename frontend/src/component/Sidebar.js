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
      }}
    >
      <button
        className="delete is-pulled-right"
        style={{ margin: '0.5rem 1rem 0 0', position: 'absolute', right: 0, top: 0, zIndex: 2 }}
        aria-label="toggle sidebar"
        onClick={onToggle}
      >
        {collapsed ? <span style={{ fontWeight: 'bold', fontSize: '1.5rem' }}>&#9776;</span> : '×'}
      </button>
      {!collapsed && (
        <div className="has-text-centered" style={{ marginTop: '2.5rem' }}>
          <img src={dev1} alt="dev1" style={{ width: '70px', borderRadius: '50%' }} />
          <div className="mt-2 mb-4">
            <div className="has-text-weight-bold is-size-6">รศ.ดร. จงสวัสดิ์ จงวัฒน์ผล</div>
            <div className="is-size-7">คณะบริหารธุรกิจ<br />สถาบันบัณฑิตพัฒนบริหารศาสตร์</div>
          </div>
          <img src={dev1} alt="dev2" style={{ width: '70px', borderRadius: '50%' }} />
          <div className="mt-2 mb-4">
            <div className="has-text-weight-bold is-size-7">ฐณพงศ์ จันทนะสุคนธ์<br /><span className='has-text-weight-normal'>Professional MBA #15<br />GenAI Developer</span></div>
          </div>
          <img src={dev1} alt="dev3" style={{ width: '70px', borderRadius: '50%' }} />
          <div className="mt-2">
            <div className="has-text-weight-bold is-size-7">คณิกร กาญจนวงศ์<br /><span className='has-text-weight-normal'>Professional MBA #15<br />UX/UI Designer</span></div>
          </div>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
