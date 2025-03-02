document.addEventListener('DOMContentLoaded', () => {
  const track = document.querySelector('.carousel-track');
  const images = document.querySelectorAll('.carousel-image');
  const prevButton = document.querySelector('.carousel-button.prev');
  const nextButton = document.querySelector('.carousel-button.next');
  
  let currentIndex = 0;
  const itemWidth = images[0].clientWidth;

  function updateCarousel() {
    track.style.transform = `translateX(-${currentIndex * itemWidth}px)`;
  }

  prevButton.addEventListener('click', () => {
    currentIndex = currentIndex > 0 ? currentIndex - 1 : images.length - 1;
    updateCarousel();
  });

  nextButton.addEventListener('click', () => {
    currentIndex = currentIndex < images.length - 1 ? currentIndex + 1 : 0;
    updateCarousel();
  });

  updateCarousel();
});