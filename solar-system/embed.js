// Solar System Simulation Embed Script
document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('solar-system-container');
  if (!container) {
    console.error('Solar system container not found. Please add a div with id="solar-system-container"');
    return;
  }

  // Set container style if not already set
  if (!container.style.position) {
    container.style.position = 'relative';
  }
  if (!container.style.height) {
    container.style.height = '600px';
  }

  // Add the info overlay
  const infoDiv = document.createElement('div');
  infoDiv.id = 'info';
  infoDiv.innerHTML = `
    <h2>Sun-Earth Simulation</h2>
    <p>Demonstrating day/night transitions</p>
    <p>Use mouse to rotate view, scroll to zoom</p>
  `;
  infoDiv.style.position = 'absolute';
  infoDiv.style.top = '10px';
  infoDiv.style.left = '10px';
  infoDiv.style.color = 'white';
  infoDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
  infoDiv.style.padding = '10px';
  infoDiv.style.borderRadius = '5px';
  infoDiv.style.pointerEvents = 'none';
  container.appendChild(infoDiv);

  // Add the controls
  const controlsDiv = document.createElement('div');
  controlsDiv.id = 'controls';
  controlsDiv.innerHTML = `
    <button id="toggleHelpers">Toggle Helpers</button>
    <button id="resetCamera">Reset Camera</button>
    <button id="topView">Top View</button>
    <div class="seasons" style="margin-top: 10px; display: flex; flex-wrap: wrap; justify-content: center;">
      <button id="summer">Summer</button>
      <button id="autumn">Autumn</button>
      <button id="winter">Winter</button>
      <button id="spring">Spring</button>
    </div>
  `;
  controlsDiv.style.position = 'absolute';
  controlsDiv.style.bottom = '10px';
  controlsDiv.style.left = '10px';
  controlsDiv.style.color = 'white';
  controlsDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
  controlsDiv.style.padding = '10px';
  controlsDiv.style.borderRadius = '5px';
  container.appendChild(controlsDiv);

  // Add the camera info
  const cameraInfoDiv = document.createElement('div');
  cameraInfoDiv.id = 'camera-info';
  cameraInfoDiv.innerHTML = 'Camera Position: (0, 0, 0)<br>Looking At: (0, 0, 0)';
  cameraInfoDiv.style.position = 'absolute';
  cameraInfoDiv.style.bottom = '10px';
  cameraInfoDiv.style.right = '10px';
  cameraInfoDiv.style.color = 'white';
  cameraInfoDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
  cameraInfoDiv.style.padding = '10px';
  cameraInfoDiv.style.borderRadius = '5px';
  cameraInfoDiv.style.fontFamily = 'monospace';
  cameraInfoDiv.style.fontSize = '12px';
  cameraInfoDiv.style.display = 'block';
  container.appendChild(cameraInfoDiv);

  // Load the main script
  const script = document.createElement('script');
  script.type = 'module';
  script.src = './assets/index-otPlMTsW.js';
  document.head.appendChild(script);

  // Add button styles
  const style = document.createElement('style');
  style.textContent = `
    #solar-system-container button {
      margin: 5px;
      padding: 5px 10px;
      cursor: pointer;
    }
  `;
  document.head.appendChild(style);
});