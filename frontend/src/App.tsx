import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import TopNav from './components/TopNav';
import CommandCenter from './pages/CommandCenter';
import LiveIntelligence from './pages/LiveIntelligence';
import UrbanMap from './pages/UrbanMap';
import UrbanIssues from './pages/UrbanIssues';
import TrafficIntelligence from './pages/TrafficIntelligence';

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <TopNav />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/live" element={<LiveIntelligence />} />
            <Route path="/map" element={<UrbanMap />} />
            <Route path="/issues" element={<UrbanIssues />} />
            <Route path="/traffic" element={<TrafficIntelligence />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;
