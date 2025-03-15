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


const thumbnailSlider = new Swiper('.thumbnail-slider', {
  slidesPerView: 3,
  spaceBetween: 10,
  navigation: {
      nextEl: '.swiper-button-next',
      prevEl: '.swiper-button-prev',
  },
  loop: false, // Ensure no infinite growth
  centeredSlides: false, // Avoid centering slides
  breakpoints: {
      768: {
          slidesPerView: 4,
      },
      1400: {
        slidesPerView: 5,
    },
    2000: {
      slidesPerView: 6,
  },

  },
});


 

  document.addEventListener("DOMContentLoaded", function () {
    // Get available and full storage from the DOM
    const availableStorage = parseInt(document.getElementById('availableStorage').innerText);
    const fullStorageCapacity = parseInt(document.getElementById('fullStorageCapacity').innerText);

    // Calculate the filled percentage of the storage
    const filledStorage = fullStorageCapacity - availableStorage;
    const filledPercentage = (filledStorage / fullStorageCapacity) * 100;

    // Set the width of the yellow fill based on the filled percentage
    const hardDiskFill = document.getElementById('hardDiskFill');
    hardDiskFill.style.width = `${filledPercentage}%`;

    // Update the text for available and full capacity
    document.getElementById('capacityText').innerHTML = `${availableStorage} GB / ${fullStorageCapacity} GB`;



});


// Function to update the big image when a thumbnail is clicked
function updateBigImage(src) {
  const bigImage = document.getElementById('bigImage');
  const bigVideoContainer = document.getElementById('bigVideoContainer');
  
  // Show the image container and hide the video container
  bigImage.style.display = 'block';  // Show image
  bigVideoContainer.style.display = 'none';  // Hide video

  // Change the image source
  bigImage.src = src;
}





// Function to update the big image when a thumbnail is clicked
function updateBigImage(src) {
  const bigImage = document.getElementById('bigImage');
  const bigVideoContainer = document.getElementById('bigVideoContainer');
  const bigVideo = document.getElementById('bigVideo');
  const videoThumbnail = document.getElementById('videoThumbnail');

  // Show the image container and hide the video container
  bigImage.style.display = 'block';  // Show image
  bigVideoContainer.style.display = 'none';  // Hide video

  // Change the image source
  bigImage.src = src;

  // Reset video iframe to stop playback when switching to image
  bigVideo.src = "";  // Reset the iframe src to stop the video
}

// Function to update the big video when the play button is clicked
function updateBigVideo(url) {
  const bigImage = document.getElementById('bigImage');
  const bigVideoContainer = document.getElementById('bigVideoContainer');
  const bigVideo = document.getElementById('bigVideo');
  const videoThumbnail = document.getElementById('videoThumbnail');

  // Hide the image and show the video
  bigImage.style.display = 'none';  // Hide the image
  bigVideoContainer.style.display = 'block';  // Show the video container

  // Extract YouTube ID from the URL
  const videoId = extractVideoId(url);

  // Show the iframe for video and start autoplay
  bigVideo.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;  // rel=0 disables showing related videos at the end

  // Optional: play the video directly (this is mostly handled by autoplay)
  bigVideo.play(); // Start playing the video

  // Hide the video thumbnail (optional)
  videoThumbnail.style.display = 'none';
}

// Function to extract YouTube video ID from URL
function extractVideoId(url) {
  const regExp = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+|(?:v|e(?:mbed)?)\/([a-zA-Z0-9_-]+))|youtu\.be\/([a-zA-Z0-9_-]+))/;
  const match = url.match(regExp);
  return match ? (match[1] || match[2]) : null;
}



//profile
const profileCircle = document.getElementById('profileCircle');
const dropdownMenu = document.getElementById('dropdownMenu');

profileCircle.addEventListener('click', function() {
    dropdownMenu.classList.toggle('hidden');
});

// Optional: Close the dropdown if clicked outside
document.addEventListener('click', function(event) {
    if (!profileCircle.contains(event.target) && !dropdownMenu.contains(event.target)) {
        dropdownMenu.classList.add('hidden');
    }
});