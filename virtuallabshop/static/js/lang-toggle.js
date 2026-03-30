/**
 * lang-toggle.js — Shared language toggle logic (EN ↔ සිංහල)
 *
 * Reads page-specific titles/descriptions from data attributes on <body>:
 *   data-title-en="..."  data-title-si="..."
 *   data-desc-en="..."   data-desc-si="..."
 */
document.addEventListener('DOMContentLoaded', function () {
    const langToggleBtn = document.getElementById('langToggleBtn');
    const langToggleBtnMobile = document.getElementById('langToggleBtnMobile');
    const body = document.body;
    const metaDescription = document.querySelector('meta[name="description"]');

    const enTitle = body.dataset.titleEn || document.title;
    const siTitle = body.dataset.titleSi || document.title;
    const enDesc = body.dataset.descEn || (metaDescription ? metaDescription.getAttribute('content') : '');
    const siDesc = body.dataset.descSi || enDesc;

    const setLanguage = (lang) => {
        const isSi = lang === 'si';
        body.classList.toggle('sinhala-mode', isSi);
        body.classList.toggle('font-sinhala', isSi);
        if (langToggleBtn) langToggleBtn.textContent = isSi ? 'EN' : 'සිංහල';

        document.title = isSi ? siTitle : enTitle;
        if (metaDescription) {
            metaDescription.setAttribute('content', isSi ? siDesc : enDesc);
        }
        localStorage.setItem('language', lang);
    };

    const toggleLanguage = () => {
        const newLang = (localStorage.getItem('language') || 'en') === 'en' ? 'si' : 'en';
        setLanguage(newLang);
    };

    langToggleBtn?.addEventListener('click', toggleLanguage);
    langToggleBtnMobile?.addEventListener('click', toggleLanguage);

    // Apply saved language on page load
    setLanguage(localStorage.getItem('language') || 'en');
});
