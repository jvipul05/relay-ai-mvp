import React from 'react';

const demoHighlights = [
  { number: '01', title: 'Understand project risk', description: 'See portfolio signals, delivery risk and task dependencies.' },
  { number: '02', title: 'Ask Relay', description: 'Explore AI answers grounded in sample project evidence.' },
  { number: '03', title: 'Review recovery actions', description: 'Walk through approval, simulated execution and verification.' },
];

export default function LoginPage({ onContinue }) {
  return (
    <main className="login-screen">
      <div className="login-orb login-orb-one" aria-hidden="true" />
      <div className="login-orb login-orb-two" aria-hidden="true" />

      <header className="login-header">
        <a className="login-brand" href="/" aria-label="Relay home">
          <span className="login-brand-mark">r.</span>
          <span className="login-brand-copy">
            <strong>relay</strong>
            <small>ORG INTELLIGENCE</small>
          </span>
        </a>
        <span className="login-header-note"><span className="login-live-dot" /> LIVE PROTOTYPE</span>
      </header>

      <div className="login-layout">
        <section className="login-story">
          <div className="login-eyebrow"><span /> ORGANIZATIONAL INTELLIGENCE, CONNECTED</div>
          <h1>See the work.<br /><span>Understand what matters.</span></h1>
          <p className="login-story-copy">
            Relay brings project signals, decisions and evidence into one place — so teams can move
            from risk to recovery with confidence.
          </p>

          <div className="login-highlights">
            {demoHighlights.map(item => (
              <article className="login-highlight" key={item.number}>
                <span className="login-highlight-number">{item.number}</span>
                <span className="login-highlight-copy">
                  <strong>{item.title}</strong>
                  <small>{item.description}</small>
                </span>
                <span className="login-highlight-arrow" aria-hidden="true">↗</span>
              </article>
            ))}
          </div>

          <div className="login-story-foot">
            <span className="login-story-foot-mark">✧</span>
            <span>One workspace for insight, decisions and follow-through.</span>
          </div>
        </section>

        <section className="login-card" aria-labelledby="login-title">
          <div className="login-card-top">
            <span className="login-card-mark">r.</span>
            <span className="login-demo-tag">HACKATHON DEMO</span>
          </div>
          <div className="login-card-intro">
            <span className="login-welcome-label">WELCOME TO RELAY</span>
            <h2 id="login-title">Explore the workspace</h2>
            <p>Step into a live demo using sample project data. No account or setup required.</p>
          </div>

          <button className="login-guest-button" type="button" onClick={onContinue}>
            <span className="login-guest-icon" aria-hidden="true">↗</span>
            <span>Continue as Guest Demo</span>
            <span className="login-guest-arrow" aria-hidden="true">→</span>
          </button>

          <div className="login-guest-note">
            <span aria-hidden="true">ⓘ</span>
            <p>Guest mode uses a shared demo workspace. Recovery actions are simulated and no external systems are changed.</p>
          </div>

          <div className="login-divider"><span>INSIDE THE DEMO</span></div>
          <ul className="login-feature-list">
            <li><span aria-hidden="true">✓</span> Portfolio and project risk intelligence</li>
            <li><span aria-hidden="true">✓</span> Evidence search and Gemini + RAG chat</li>
            <li><span aria-hidden="true">✓</span> Approval-controlled demo actions</li>
          </ul>

          <div className="login-card-footer">
            <span className="login-lock" aria-hidden="true">◇</span>
            <span>Guest demo · Synthetic project records</span>
          </div>
        </section>
      </div>

      <footer className="login-footer">
        <span>RELAY · ORGANIZATIONAL INTELLIGENCE</span>
        <span>DEMO MODE <i /> BUILT FOR BETTER DECISIONS</span>
      </footer>
    </main>
  );
}
