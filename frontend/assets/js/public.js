/**
 * Arcteron Trust — Public Pages JavaScript
 * Handles: News Ticker, Hero Slideshow, Nav Dropdowns,
 *          Mobile Drawer, Scroll Animations, Testimonials, Back-to-Top
 */

// ============================================================
// NEWS TICKER — duplicate items for seamless infinite scroll
// ============================================================
const TICKER_ITEMS = [
    '🏦 Federal Reserve holds interest rates steady at 5.25%–5.50% for the fourth consecutive meeting',
    '📈 Arcteron Trust reports record Q1 2025 earnings — assets under management cross $2.8 billion',
    '🏠 30-year fixed mortgage rates ease to 6.82% — lowest in 14 months',
    '💳 New FDIC guidance expands deposit insurance clarity for joint accounts',
    '📊 US banking sector shows resilience with Tier 1 capital ratios averaging 14.2%',
    '🌟 Arcteron Trust named among "Best Private Banks in New England" by Boston Business Journal',
    '💰 CD rates remain competitive — Arcteron Trust offers 5.10% APY on 12-month certificates',
    '🔒 Arcteron Trust upgrades to military-grade 512-bit encryption across all digital platforms',
    '📉 Consumer credit growth slows to 2.1% annually, signaling cautious household spending',
    '🏛️ Senate Banking Committee advances new open banking framework legislation',
    '✅ Arcteron Trust expands wealth management division with three new senior advisors in Boston',
    '📱 Mobile banking adoption reaches 78% among US adults under 45, per Federal Reserve report',
];

function initTicker() {
    const track = document.querySelector('.ticker-track');
    if (!track) return;

    // Build items HTML
    const itemsHTML = TICKER_ITEMS.map(text =>
        `<span class="ticker-item">${text}</span>`
    ).join('');

    // Duplicate for seamless loop
    track.innerHTML = itemsHTML + itemsHTML;
}

// ============================================================
// HERO SLIDESHOW
// ============================================================
const HERO_SLIDES = [
    {
        bg: 'https://images.unsplash.com/photo-1486325212027-8081e485255e?w=1600&q=85&auto=format&fit=crop',
        overlay: 'linear-gradient(105deg, rgba(10,12,16,0.88) 0%, rgba(10,12,16,0.55) 60%, rgba(10,12,16,0.30) 100%)',
        eyebrow: 'Private Banking · Boston, MA',
        title: 'Banking Built on\nTrust & Integrity',
        subtitle: 'Experience personalized financial services crafted for individuals, families, and businesses who expect more from their bank.',
        cta1: { text: 'Open an Account', href: '/frontend/pages/register.html' },
        cta2: { text: 'Learn More', href: '/frontend/pages/about.html' },
    },
    {
        bg: 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?w=1600&q=85&auto=format&fit=crop',
        overlay: 'linear-gradient(115deg, rgba(5,8,20,0.92) 0%, rgba(5,8,20,0.60) 55%, rgba(5,8,20,0.25) 100%)',
        eyebrow: 'Wealth Management',
        title: 'Grow & Protect\nYour Wealth',
        subtitle: 'Our seasoned investment advisors craft bespoke strategies aligned with your financial goals and legacy ambitions.',
        cta1: { text: 'Explore Wealth Services', href: '/frontend/pages/wealth-management.html' },
        cta2: { text: 'Meet Our Advisors', href: '/frontend/pages/about.html' },
    },
    {
        bg: 'https://images.unsplash.com/photo-1560520031-3a4dc4e9de0c?w=1600&q=85&auto=format&fit=crop',
        overlay: 'linear-gradient(100deg, rgba(8,10,18,0.90) 0%, rgba(8,10,18,0.58) 58%, rgba(8,10,18,0.28) 100%)',
        eyebrow: 'Business Banking',
        title: 'Banking That\nFuels Business Growth',
        subtitle: 'From startup checking accounts to enterprise treasury management, Arcteron Trust is your partner for every stage of business.',
        cta1: { text: 'Business Solutions', href: '/frontend/pages/business-banking.html' },
        cta2: { text: 'Talk to an Advisor', href: '/frontend/pages/contact.html' },
    },
];

let heroIdx = 0;
let heroTimer = null;
let heroSlides = [];
let heroDots = [];

function buildHero() {
    const section = document.getElementById('heroSection');
    if (!section) return;

    // Build slides
    const slidesContainer = document.getElementById('heroSlides');
    if (!slidesContainer) return;

    HERO_SLIDES.forEach((s, i) => {
        const slide = document.createElement('div');
        slide.className = 'hero-slide' + (i === 0 ? ' active' : '');
        slide.innerHTML = `
      <div class="hero-slide-bg" style="background-image:url('${s.bg}')"></div>
      <div class="hero-slide-overlay" style="background:${s.overlay}"></div>
      <div class="hero-slide-content pub-container">
        <div class="hero-eyebrow">${s.eyebrow}</div>
        <h1 class="hero-title">${s.title.replace('\n', '<br>')}</h1>
        <p class="hero-subtitle">${s.subtitle}</p>
        <div class="hero-actions">
          <a href="${s.cta1.href}" class="hero-btn-primary">${s.cta1.text}</a>
          <a href="${s.cta2.href}" class="hero-btn-secondary">${s.cta2.text}</a>
        </div>
      </div>`;
        slidesContainer.appendChild(slide);
    });

    heroSlides = slidesContainer.querySelectorAll('.hero-slide');

    // Build dots
    const dotsEl = document.getElementById('heroDots');
    HERO_SLIDES.forEach((_, i) => {
        const dot = document.createElement('button');
        dot.className = 'hero-dot' + (i === 0 ? ' active' : '');
        dot.setAttribute('aria-label', `Go to slide ${i + 1}`);
        dot.addEventListener('click', () => goToSlide(i));
        dotsEl.appendChild(dot);
    });
    heroDots = dotsEl.querySelectorAll('.hero-dot');

    startHeroTimer();
}

function goToSlide(idx) {
    heroSlides[heroIdx].classList.remove('active');
    heroDots[heroIdx].classList.remove('active');
    heroIdx = (idx + HERO_SLIDES.length) % HERO_SLIDES.length;
    heroSlides[heroIdx].classList.add('active');
    heroDots[heroIdx].classList.add('active');
}

function nextSlide() { goToSlide(heroIdx + 1); }
function prevSlide() { goToSlide(heroIdx - 1); }

function startHeroTimer() {
    clearInterval(heroTimer);
    heroTimer = setInterval(nextSlide, 6000);
}

function initHero() {
    buildHero();

    const prevBtn = document.getElementById('heroPrev');
    const nextBtn = document.getElementById('heroNext');

    if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); startHeroTimer(); });
    if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); startHeroTimer(); });
}

// ============================================================
// NAV — scroll shadow + mobile drawer
// ============================================================
function initNav() {
    const nav = document.querySelector('.pub-nav');
    if (!nav) return;

    // Scroll shadow
    window.addEventListener('scroll', () => {
        nav.classList.toggle('scrolled', window.scrollY > 20);
    }, { passive: true });

    // Hamburger
    const hamburger = document.getElementById('navHamburger');
    const drawer = document.getElementById('mobileDrawer');
    const overlay = drawer?.querySelector('.drawer-overlay');
    const closeBtn = document.getElementById('drawerClose');

    function openDrawer() {
        drawer.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    function closeDrawer() {
        drawer.classList.remove('open');
        document.body.style.overflow = '';
    }

    if (hamburger) hamburger.addEventListener('click', openDrawer);
    if (overlay) overlay.addEventListener('click', closeDrawer);
    if (closeBtn) closeBtn.addEventListener('click', closeDrawer);

    // Drawer accordion
    document.querySelectorAll('.drawer-nav-trigger').forEach(btn => {
        btn.addEventListener('click', () => {
            const isOpen = btn.classList.contains('open');
            // Close all
            document.querySelectorAll('.drawer-nav-trigger').forEach(b => b.classList.remove('open'));
            document.querySelectorAll('.drawer-sub-links').forEach(s => s.classList.remove('open'));
            // Toggle clicked
            if (!isOpen) {
                btn.classList.add('open');
                const subLinks = btn.nextElementSibling;
                if (subLinks) subLinks.classList.add('open');
            }
        });
    });

    // Close drawer on link click
    document.querySelectorAll('#mobileDrawer a').forEach(link => {
        link.addEventListener('click', closeDrawer);
    });
}

// ============================================================
// TESTIMONIALS CAROUSEL
// ============================================================
const TESTIMONIALS = [
    {
        text: "Arcteron Trust completely transformed how I think about wealth management. My advisor created a retirement plan that I never thought was possible at my age. The personalized service is truly unmatched.",
        name: "Margaret T.",
        role: "Retired Executive, Cambridge MA",
        initials: "MT",
        stars: 5,
    },
    {
        text: "Switching our business banking to Arcteron was the best decision we made last quarter. The treasury management tools alone saved us countless hours. Their team is responsive, knowledgeable, and genuinely invested in our success.",
        name: "David K.",
        role: "CEO, Harborview Ventures",
        initials: "DK",
        stars: 5,
    },
    {
        text: "The mortgage process was seamless from start to finish. Arcteron's loan officers walked us through every step and got us a rate that no other Boston bank could match. We closed on our dream home in Beacon Hill.",
        name: "Sofia & James R.",
        role: "Homeowners, Boston MA",
        initials: "SR",
        stars: 5,
    },
    {
        text: "As a first-generation immigrant building credit from scratch, Arcteron Trust was patient, educational, and empowering. Three years later, I have an 800+ credit score and a thriving small business account.",
        name: "Emmanuel O.",
        role: "Entrepreneur, Roxbury MA",
        initials: "EO",
        stars: 5,
    },
    {
        text: "I've banked with the big national banks for 20 years. Arcteron Trust reminded me what banking should actually feel like — your banker knows your name, your goals, and your family. Truly a community institution.",
        name: "Patricia N.",
        role: "Real Estate Investor, South Boston",
        initials: "PN",
        stars: 5,
    },
];

let testimonialIdx = 0;
let testimonialTimer = null;

function buildTestimonials() {
    const track = document.getElementById('testimonialTrack');
    if (!track) return;

    TESTIMONIALS.forEach(t => {
        const card = document.createElement('div');
        card.className = 'testimonial-card';
        card.innerHTML = `
      <div class="testimonial-inner">
        <div class="testimonial-quote-mark">"</div>
        <div class="testimonial-stars">${'<span>★</span>'.repeat(t.stars)}</div>
        <p class="testimonial-text">"${t.text}"</p>
        <div class="testimonial-author">
          <div class="testimonial-avatar">${t.initials}</div>
          <div>
            <div class="testimonial-name">${t.name}</div>
            <div class="testimonial-role">${t.role}</div>
          </div>
        </div>
      </div>`;
        track.appendChild(card);
    });

    // Build dots
    const dotsEl = document.getElementById('testimonialDots');
    TESTIMONIALS.forEach((_, i) => {
        const dot = document.createElement('button');
        dot.className = 'testimonial-dot' + (i === 0 ? ' active' : '');
        dot.setAttribute('aria-label', `Testimonial ${i + 1}`);
        dot.addEventListener('click', () => goToTestimonial(i));
        dotsEl.appendChild(dot);
    });

    startTestimonialTimer();
}

function goToTestimonial(idx) {
    const track = document.getElementById('testimonialTrack');
    const dots = document.querySelectorAll('.testimonial-dot');
    if (!track) return;

    dots[testimonialIdx]?.classList.remove('active');
    testimonialIdx = (idx + TESTIMONIALS.length) % TESTIMONIALS.length;
    track.style.transform = `translateX(-${testimonialIdx * 100}%)`;
    dots[testimonialIdx]?.classList.add('active');
}

function startTestimonialTimer() {
    clearInterval(testimonialTimer);
    testimonialTimer = setInterval(() => goToTestimonial(testimonialIdx + 1), 5000);
}

function initTestimonials() {
    buildTestimonials();

    const prevBtn = document.getElementById('testimonialPrev');
    const nextBtn = document.getElementById('testimonialNext');

    if (prevBtn) prevBtn.addEventListener('click', () => { goToTestimonial(testimonialIdx - 1); startTestimonialTimer(); });
    if (nextBtn) nextBtn.addEventListener('click', () => { goToTestimonial(testimonialIdx + 1); startTestimonialTimer(); });
}

// ============================================================
// SCROLL REVEAL ANIMATIONS
// ============================================================
function initScrollReveal() {
    const elements = document.querySelectorAll('.reveal, .reveal-left, .reveal-right, .reveal-scale');
    if (!elements.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });

    elements.forEach(el => observer.observe(el));
}

// ============================================================
// BACK TO TOP
// ============================================================
function initBackToTop() {
    const btn = document.getElementById('backToTop');
    if (!btn) return;

    window.addEventListener('scroll', () => {
        btn.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    btn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
}

// ============================================================
// THEME TOGGLE
// ============================================================
function initPublicTheme() {
    const btn = document.getElementById('themeToggle');
    if (!btn) return;

    const updateIcon = () => {
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
        btn.innerHTML = isDark
            ? `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`
            : `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
    };

    btn.addEventListener('click', () => {
        Theme.toggle();
        updateIcon();
    });

    updateIcon();
}

// ============================================================
// ANIMATED STATS COUNTER
// ============================================================
function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    if (!counters.length) return;

    const observer = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseFloat(el.dataset.count);
                const prefix = el.dataset.prefix || '';
                const suffix = el.dataset.suffix || '';
                const decimals = el.dataset.decimals ? parseInt(el.dataset.decimals) : 0;
                const duration = 1800;
                const start = performance.now();

                function step(now) {
                    const elapsed = now - start;
                    const progress = Math.min(elapsed / duration, 1);
                    const eased = 1 - Math.pow(1 - progress, 3);
                    const value = (eased * target).toFixed(decimals);
                    el.textContent = prefix + value + suffix;
                    if (progress < 1) requestAnimationFrame(step);
                }
                requestAnimationFrame(step);
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.5 });

    counters.forEach(el => observer.observe(el));
}

// ============================================================
// COPYRIGHT YEAR
// ============================================================
function initYear() {
    document.querySelectorAll('.current-year').forEach(el => {
        el.textContent = new Date().getFullYear();
    });
}

// ============================================================
// INIT ALL
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initTicker();
    initHero();
    initNav();
    initTestimonials();
    initScrollReveal();
    initBackToTop();
    initPublicTheme();
    initCounters();
    initYear();
});
