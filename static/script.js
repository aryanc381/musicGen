// Changing Words Animation (only run if changing-word element exists)
const wordElement = document.getElementById('changing-word');
if (wordElement) {
  const words = ["everyone", "artists", "composers", "explorers", "musicians", "dreamers"];
  let wordIndex = 0;

  wordElement.style.transition = 'opacity 0.5s ease';

  setInterval(() => {
    wordElement.style.opacity = 0; // Fade out
    setTimeout(() => {
      wordIndex = (wordIndex + 1) % words.length;
      wordElement.textContent = words[wordIndex];
      wordElement.style.opacity = 1; // Fade in
    }, 350);
  }, 4500);
}

// Theme Toggle Script
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;

// Load previous mode
if (localStorage.getItem('theme') === 'light') {
  body.classList.add('light-mode');
  themeToggle.checked = true;
}

themeToggle.addEventListener('change', () => {
  if (themeToggle.checked) {
    body.classList.add('light-mode');
    localStorage.setItem('theme', 'light');
  } else {
    body.classList.remove('light-mode');
    localStorage.setItem('theme', 'dark');
  }
});
