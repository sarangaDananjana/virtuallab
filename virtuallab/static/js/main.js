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



//slider 
document.addEventListener('DOMContentLoaded', () => {
    const sliderWrapper = document.querySelector('.slider-wrapper');
    const slider = document.querySelector('.slider');
    const slides = document.querySelectorAll('.slide');
    const dotsContainer = document.querySelector('.slider-dots');
    let currentSlide = 0;
    const totalSlides = slides.length;

    // Create dots dynamically
    const createDots = () => {
        for (let i = 0; i < totalSlides; i++) {
            const dot = document.createElement('div');
            dot.classList.add('dot');
            if (i === 0) dot.classList.add('active'); // Set the first dot as active
            dot.dataset.index = i;
            dotsContainer.appendChild(dot);
        }
    };

    const updateSliderPosition = () => {
        const slideWidth = sliderWrapper.offsetWidth;
        slider.style.transform = `translateX(-${currentSlide * slideWidth}px)`;

        // Update active dot
        document.querySelectorAll('.slider-dots .dot').forEach((dot, index) => {
            dot.classList.toggle('active', index === currentSlide);
        });
    };

    const moveToSlide = (index) => {
        currentSlide = index;
        updateSliderPosition();
    };

    // Add click events for dots
    dotsContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('dot')) {
            const index = parseInt(e.target.dataset.index, 10);
            moveToSlide(index);
        }
    });

    // Mouse and touch drag functionality
    let isDragging = false;
    let startX = 0;
    let currentTranslate = 0;
    let prevTranslate = 0;

    const setSliderPosition = (translateX) => {
        slider.style.transform = `translateX(${translateX}px)`;
    };

    const moveToClosestSlide = () => {
        const slideWidth = sliderWrapper.offsetWidth;
        const threshold = slideWidth / 4; // Drag threshold to move to the next slide
        const offset = currentTranslate - prevTranslate;

        if (offset > threshold) {
            currentSlide = Math.max(0, currentSlide - 1); // Move to the previous slide
        } else if (offset < -threshold) {
            currentSlide = Math.min(totalSlides - 1, currentSlide + 1); // Move to the next slide
        }
        updateSliderPosition();
    };

    const startDrag = (clientX) => {
        isDragging = true;
        startX = clientX;
        prevTranslate = -currentSlide * sliderWrapper.offsetWidth;
        sliderWrapper.style.cursor = 'grabbing';
    };

    const dragMove = (clientX) => {
        if (!isDragging) return;
        const dx = clientX - startX;
        currentTranslate = prevTranslate + dx;
        setSliderPosition(currentTranslate);
    };

    const endDrag = () => {
        isDragging = false;
        sliderWrapper.style.cursor = 'grab';
        moveToClosestSlide();
    };

    // Event listeners for mouse drag
    sliderWrapper.addEventListener('mousedown', (e) => {
        e.preventDefault(); // Prevent default behavior to avoid screen shaking
        startDrag(e.clientX);
    });

    sliderWrapper.addEventListener('mousemove', (e) => {
        e.preventDefault(); // Prevent default behavior
        dragMove(e.clientX);
    });

    sliderWrapper.addEventListener('mouseup', () => {
        endDrag();
    });

    sliderWrapper.addEventListener('mouseleave', () => {
        if (isDragging) endDrag();
    });

    // Event listeners for touch drag (mobile)
    sliderWrapper.addEventListener('touchstart', (e) => {
        startDrag(e.touches[0].clientX);
    });

    sliderWrapper.addEventListener('touchmove', (e) => {
        e.preventDefault(); // Prevent scrolling during dragging
        dragMove(e.touches[0].clientX);
    });

    sliderWrapper.addEventListener('touchend', () => {
        endDrag();
    });

    // Initialize
    createDots();
    updateSliderPosition();

    // Update on window resize
    window.addEventListener('resize', updateSliderPosition);
});




document.addEventListener("DOMContentLoaded", function () {
    var swiper = new Swiper(".promotions-slider", {
        slidesPerView: 1.2,
        spaceBetween: 20,
        loop: false,
        speed: 600,
        navigation: {
            nextEl: ".next",
            prevEl: ".prev",
        },
        breakpoints: {
            370: {
                slidesPerView: 1.5,
            },
            768: {
                slidesPerView: 3.2,
            },
            1024: {
                slidesPerView: 3.8,
            },

            1400: {
                slidesPerView: 5.5,
            }
        },
    });
});

document.addEventListener("DOMContentLoaded", function () {
    var swiper = new Swiper(".hard-slider", {
        slidesPerView: 1.2,

        loop: false,
        speed: 600,
        navigation: {
            nextEl: ".next",
            prevEl: ".prev",
        },
        breakpoints: {
            370: {
                slidesPerView: 1.5,
            },
            768: {
                slidesPerView: 3,
            },
            1024: {
                slidesPerView: 4.2,
            },

            1400: {
                slidesPerView: 4,
            },
            2000: {
                slidesPerView: 5.5,
            }
        },
    });
});

//hero image section

document.addEventListener("DOMContentLoaded", () => {
    const heroImg = document.querySelector(".lg-hero-img img.main-img"); // Main hero image
    const heroLogo = document.querySelector(".lg-hero-logo-container img"); // Main hero logo
    const heroTitle = document.querySelector(".lg-hero-img-componants h1"); // Hero title
    const heroParagraph = document.querySelector(".lg-hero-img-componants p"); // Hero paragraph
    const heroButton = document.querySelector(".lg-hero-img-componants button"); // Hero button

    const sliderComponents = document.querySelectorAll(".slider-componant"); // All slider components
    let currentIndex = 0;
    let autoSlideInterval;

    const updateHeroContent = (index) => {
        if (index !== undefined) currentIndex = index; // Update index if provided

        const currentSlider = sliderComponents[currentIndex];

        // Update hero image
        const newImageSrc = currentSlider.querySelector(".slider-img").getAttribute("src");
        heroImg.classList.remove("hero-float-in"); // Reset animation class
        void heroImg.offsetWidth; // Trigger reflow to restart the animation
        heroImg.classList.add("hero-float-in");
        heroImg.setAttribute("src", newImageSrc);

        // Update hero logo
        const newLogoSrc = currentSlider.querySelector(".slider-logo-container img").getAttribute("src");
        heroLogo.classList.remove("hero-float-in");
        void heroLogo.offsetWidth;
        heroLogo.classList.add("hero-float-in");
        heroLogo.setAttribute("src", newLogoSrc);

        // Update hero title
        const newTitle = currentSlider.querySelector("h1").textContent;
        heroTitle.textContent = newTitle;
        heroTitle.classList.remove("hero-float-in");
        void heroTitle.offsetWidth;
        heroTitle.classList.add("hero-float-in");
        heroTitle.setAttribute("src", newTitle);

        // Update hero paragraph
        const newParagraph = currentSlider.querySelector("p").textContent;
        heroParagraph.textContent = newParagraph;
        heroParagraph.classList.remove("hero-float-in");
        void heroParagraph.offsetWidth;
        heroParagraph.classList.add("hero-float-in");
        heroParagraph.setAttribute("src", newParagraph);

        // Update hero button
        const newButtonText = currentSlider.querySelector("button").textContent;
        heroButton.textContent = newButtonText;
        heroButton.classList.remove("hero-float-in");
        void heroButton.offsetWidth;
        heroButton.classList.add("hero-float-in");
        heroButton.setAttribute("src", newButtonText);

        // Manage active class for slider components
        sliderComponents.forEach((component, index) => {
            component.classList.toggle("active", index === currentIndex);
        });
    };

    const startAutoSlide = () => {
        autoSlideInterval = setInterval(() => {
            currentIndex = (currentIndex + 1) % sliderComponents.length;
            updateHeroContent();
        }, 5000); // 5-second interval
    };

    const resetAutoSlide = () => {
        clearInterval(autoSlideInterval); // Clear existing interval
        startAutoSlide(); // Start a new interval
    };

    // Add click event listeners to slider components
    sliderComponents.forEach((slider, index) => {
        slider.addEventListener("click", () => {
            updateHeroContent(index); // Update content based on clicked slider
            resetAutoSlide(); // Restart the 5-second interval
        });
    });

    // Start the initial auto-slide
    startAutoSlide();

    // Initialize with the first slider content
    updateHeroContent();
});




//profile
const profileCircle = document.getElementById('profileCircle');
const dropdownMenu = document.getElementById('dropdownMenu');

profileCircle.addEventListener('click', function () {
    dropdownMenu.classList.toggle('hidden');
});

// Optional: Close the dropdown if clicked outside
document.addEventListener('click', function (event) {
    if (!profileCircle.contains(event.target) && !dropdownMenu.contains(event.target)) {
        dropdownMenu.classList.add('hidden');
    }
});