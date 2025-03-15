// Grab elements
const selectElement = selector => {
    const element = document.querySelector(selector)
    if (element) return element;
    throw new Error(`Somthing went,make sure that $(selector) exist or is typed correctly.`);

};

//Nav styles on scroll
const scrollHeader = () => {
    const headerElement = selectElement('#header');
    if (this.scrollY >= 15) {
        headerElement.classList.add('activated');

    } else {
        headerElement.classList.remove('activated');
    }
};
// Open menu & search pop-up
window.addEventListener('scroll', scrollHeader);

const menuToggleIcon = selectElement("#menu-toggle-icon");

const toggleMenu = () => {
    const mobileMenu = selectElement('#menu');
    mobileMenu.classList.toggle('activated');
    menuToggleIcon.classList.toggle('activated');
};
// Open/Close search form popup
menuToggleIcon.addEventListener('click', toggleMenu);


const navLinks = document.querySelectorAll('.list-link');
const sections = document.querySelectorAll('section'); 


function highlightNavOnScroll() {
    let scrollPosition = window.scrollY;

    sections.forEach((section) => {
        const sectionTop = section.offsetTop - 100;// Adjust this offset according to your header height
        const sectionHeight = section.offsetHeight;
        const sectionId = section.getAttribute('id');

        // Check if the scroll position is within this section
        if (scrollPosition >= sectionTop && scrollPosition < sectionTop + sectionHeight) {
            
            navLinks.forEach((link) => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${sectionId}`) {
                    link.classList.add('active');
                }
            });
        }
    });
}


function displayFileName(input) {
    const fileName = input.files.length > 0 ? input.files[0].name : "No file chosen";
    document.getElementById('file-name').textContent = fileName;
}

