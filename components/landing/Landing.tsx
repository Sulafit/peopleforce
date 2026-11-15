import Link from "next/link";
import { CheckIcon, LogoIcon } from "@/components/icons";
import { StartCta } from "@/components/landing/StartCta";

const STEPS = [
  {
    title: "Learn one thing",
    text: "Short lessons on what clients look for: a clear offer, proof of work, a profile people can find.",
  },
  {
    title: "Apply it to yourself",
    text: "Every lesson has an exercise built on your own skills and experience, not a made-up example.",
  },
  {
    title: "Keep a real asset",
    text: "What you write is saved to your profile and reused later: your offer becomes your bio, your bio becomes your Upwork overview.",
  },
] as const;

const LEVELS = [
  { theme: "yellow", title: "Your freelance offer", text: "Decide what you sell and say it clearly." },
  { theme: "blue", title: "LinkedIn profile", text: "A profile people can find, and your first project post." },
  { theme: "violet", title: "Portfolio", text: "One real case study on a public page." },
  { theme: "green", title: "Upwork & Fiverr", text: "Marketplace profiles and your first proposal." },
  { theme: "orange", title: "Client conversations", text: "Practice the replies that decide a deal." },
  { theme: "pink", title: "Deals & documents", text: "Scope, milestones and payment, written down." },
] as const;

const ASSETS = [
  "A freelance offer a client understands",
  "A professional bio you can reuse anywhere",
  "A portfolio case study",
  "Drafts for Upwork, Fiverr and LinkedIn",
  "A first proposal for a real job post",
  "Practiced answers to common client questions",
];

const FAQ = [
  {
    q: "Is this a video course?",
    a: "No. Lessons are short and hands-on. You read a little, then do an exercise that produces something you keep, such as your offer or your bio.",
  },
  {
    q: "Who is it for?",
    a: "Right now, software developers who want to start freelancing or get more from it. Design, marketing and writing paths are planned.",
  },
  {
    q: "Do I need freelance experience?",
    a: "No. The first question we ask is where you are today, and the examples in your lessons are matched to your answers.",
  },
  {
    q: "Does AI write my profile for me?",
    a: "AI gives feedback on what you write and can prepare drafts from your own saved answers. It never adds clients, results or experience you did not give it, and nothing is final until you approve it.",
  },
  {
    q: "How do I sign in?",
    a: "With your email. We send you a link that signs you in, so there is no password to remember.",
  },
];

/** Public landing page. Static content, rendered on the server. */
export function Landing() {
  return (
    <div className="wrap t-yellow">
      <header className="topbar">
        <Link className="brand" href="/">
          <LogoIcon />
          PeopleForce
        </Link>
        <div className="pills">
          <Link className="link-btn" href="/login">
            Sign in
          </Link>
          <StartCta location="header" label="Get started" size="sm" />
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero__text">
            <span className="cap muted">For software developers · more fields coming</span>
            <h1>Turn your skills into a freelance business</h1>
            <p className="hero__lead">
              PeopleForce is a step-by-step path from skilled professional to independent freelancer. Learn something,
              apply it, and keep a real asset every time: an offer, a bio, a portfolio, a profile.
            </p>
            <div className="actions">
              <StartCta location="hero" size="lg" />
            </div>
            <p className="hint">Seven quick questions. You see your plan before you sign up.</p>
          </div>
          <div className="tower" aria-hidden="true">
            {LEVELS.map((level, index) => (
              <div key={level.title} className={`slab t-${level.theme} slab--solid${index === LEVELS.length - 1 ? " slab--float" : ""}`} />
            ))}
          </div>
        </section>

        <section className="landing-section" aria-labelledby="how-title">
          <h2 id="how-title" className="section-title">
            Learn it, apply it, keep it
          </h2>
          <ol className="info-grid">
            {STEPS.map((step, index) => (
              <li key={step.title} className="info-card">
                <span className="part__n">{index + 1}</span>
                <h3>{step.title}</h3>
                <p>{step.text}</p>
              </li>
            ))}
          </ol>
          <div>
            <StartCta location="how" />
          </div>
        </section>

        <section className="landing-section" aria-labelledby="path-title">
          <h2 id="path-title" className="section-title">
            A road that keeps growing
          </h2>
          <p className="section-lead">
            Six levels are mapped out today and more are on the way. Each builds on the one before; the examples,
            suggestions and drafts follow your specialization and your goal.
          </p>
          <ol className="info-grid">
            {LEVELS.map((level, index) => (
              <li key={level.title} className={`sign sign--flat t-${level.theme}`}>
                <span className="sign__badge" aria-hidden="true">
                  {index + 1}
                </span>
                <div className="sign__body">
                  <h3 className="sign__title sign__title--sm">{level.title}</h3>
                  <p className="sign__blurb">{level.text}</p>
                </div>
              </li>
            ))}
          </ol>
          <div>
            <StartCta location="path" label="See my personal path" />
          </div>
        </section>

        <section className="landing-section" aria-labelledby="assets-title">
          <h2 id="assets-title" className="section-title">
            What you build along the way
          </h2>
          <ul className="asset-list">
            {ASSETS.map((asset) => (
              <li key={asset} className="check">
                <span className="check__mark" aria-hidden="true">
                  <CheckIcon />
                </span>
                {asset}
              </li>
            ))}
          </ul>
          <div className="pills">
            <span className="cap muted">Prepared for</span>
            {["Upwork", "Fiverr", "LinkedIn", "Direct clients"].map((platform) => (
              <span key={platform} className="pill pill--sm">
                {platform}
              </span>
            ))}
          </div>
          <p className="hint">
            PeopleForce is not affiliated with these platforms. You publish your own content there; nothing is posted for
            you.
          </p>
        </section>

        <section className="landing-section" aria-labelledby="faq-title">
          <h2 id="faq-title" className="section-title">
            Questions
          </h2>
          <div className="faq">
            {FAQ.map((item) => (
              <details key={item.q}>
                <summary>{item.q}</summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>

        <section className="final-cta" aria-labelledby="final-title">
          <h2 id="final-title" className="section-title">
            Your first lesson takes about fifteen minutes
          </h2>
          <p className="section-lead">Answer seven questions, see your path, and start with your freelance offer.</p>
          <StartCta location="final" size="lg" />
        </section>
      </main>

      <footer className="site-foot">PeopleForce · Practical learning for independent professionals</footer>
    </div>
  );
}
