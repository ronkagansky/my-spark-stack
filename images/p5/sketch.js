let x, y, vx, vy;
let size = 30;

function setup() {
  createCanvas(windowWidth, windowHeight);
  // Start circle in middle of screen
  x = width / 2;
  y = height / 2;
  // Give it some initial velocity
  vx = 3;
  vy = 2;
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

function draw() {
  background(0);

  // Update position
  x += vx;
  y += vy;

  // Bounce off walls
  if (x + size / 2 > width || x - size / 2 < 0) vx *= -1;
  if (y + size / 2 > height || y - size / 2 < 0) vy *= -1;

  // Draw circle
  fill(255);
  noStroke();
  circle(x, y, size);
}
