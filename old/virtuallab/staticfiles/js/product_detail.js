// Initialize Swiper for the bottom slider
const thumbnailSlider = new Swiper('.thumbnail-slider', {
    slidesPerView: 3,
    spaceBetween: 10,
    navigation: {
      nextEl: '.swiper-button-next',
      prevEl: '.swiper-button-prev',
    },
    breakpoints: {
       
        1024: { 
            slidesPerView: 4,
        }
    },
  });
  
  // Function to update the big image when a thumbnail is clicked
  function updateBigImage(src) {
    const bigImage = document.getElementById('bigImage');
  
    // Add the animation class
    bigImage.classList.remove('animate-slide'); // Reset animation
    void bigImage.offsetWidth; // Trigger reflow to restart the animation
    bigImage.classList.add('animate-slide'); // Add animation class
  
    // Update the image source
    bigImage.src = src;
  }
  
  function updateBigImage(src) {
    const bigImageContainer = document.getElementById('bigImageContainer');
    bigImageContainer.innerHTML = `<img id="bigImage" src="${src}" alt="Big Image">`;
  }
  
// Function to update the big image
function updateBigImage(src) {
    const bigImage = document.getElementById('bigImage');
    const bigVideo = document.getElementById('bigVideo');
    bigImage.style.display = 'block'; // Show image
    bigVideo.style.display = 'none';  // Hide video
    bigImage.src = src;              // Change image source
  }
  
  // Function to update the big video
  function updateBigVideo(src) {
    const bigImage = document.getElementById('bigImage');
    const bigVideo = document.getElementById('bigVideo');
    bigImage.style.display = 'none'; // Hide image
    bigVideo.style.display = 'block'; // Show video
    bigVideo.src = src;              // Set video source
    bigVideo.play();                 // Start video playback
  }
  
  