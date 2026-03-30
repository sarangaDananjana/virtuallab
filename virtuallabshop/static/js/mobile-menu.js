/**
 * mobile-menu.js — Shared mobile menu open/close/overlay logic
 * Used by base.html on every page with a header.
 */
document.addEventListener('DOMContentLoaded', function () {
    const navToggle = document.getElementById('navToggle');
    const closeNav = document.getElementById('closeNav');
    const mobileMenuContainer = document.getElementById('mobileMenuContainer');
    const mobileMenu = document.getElementById('mobileMenu');
    const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
    const mobileMenuLinks = document.querySelectorAll('.mobile-menu-link');

    const openMenu = () => {
        if (!mobileMenuContainer) return;
        mobileMenuContainer.classList.remove('pointer-events-none');
        mobileMenuOverlay.classList.remove('opacity-0');
        mobileMenu.classList.remove('translate-x-full');
        document.body.style.overflow = 'hidden';
    };
    const closeMenu = () => {
        if (!mobileMenuContainer) return;
        mobileMenuOverlay.classList.add('opacity-0');
        mobileMenu.classList.add('translate-x-full');
        document.body.style.overflow = '';
        setTimeout(() => { mobileMenuContainer.classList.add('pointer-events-none'); }, 300);
    };

    navToggle?.addEventListener('click', openMenu);
    closeNav?.addEventListener('click', closeMenu);
    mobileMenuOverlay?.addEventListener('click', closeMenu);
    mobileMenuLinks.forEach(link => link.addEventListener('click', closeMenu));
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && mobileMenuContainer && !mobileMenuContainer.classList.contains('pointer-events-none')) {
            closeMenu();
        }
    });
});
