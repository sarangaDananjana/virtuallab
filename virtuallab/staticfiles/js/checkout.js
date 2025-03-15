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


//bank detials show

document.addEventListener('DOMContentLoaded', function() {
    // Get the radio buttons and the sections to toggle
    const slipRadio = document.getElementById('slip');
    const userDetailsSection = document.getElementById('user-details-section');
    const slipUploadSection = document.getElementById('slip-upload-section');

    // Function to toggle visibility based on payment method selection
    function toggleSections() {
        if (slipRadio.checked) {
            userDetailsSection.style.display = 'block'; // Show user details
            slipUploadSection.style.display = 'block'; // Show slip upload section
        } else {
            userDetailsSection.style.display = 'none'; // Hide user details
            slipUploadSection.style.display = 'none'; // Hide slip upload section
        }
    }

    // Initially check the status of the radio button on page load
    toggleSections();

    // Add event listener to the radio buttons
    slipRadio.addEventListener('change', toggleSections);
});
