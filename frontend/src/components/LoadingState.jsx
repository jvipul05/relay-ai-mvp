import React from 'react';
export default function LoadingState({ label = 'Loading Relay workspace…' }) { return <div className="loading-state"><span className="spinner"/><span>{label}</span></div>; }
