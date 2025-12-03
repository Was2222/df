const { ipcRenderer } = require("electron");

window.addEventListener("DOMContentLoaded", () => {
  // CSS to hide the header
  const customCSS = `
        header {
            display: none;
        }
        .q-page-container {
            z-index: 1;
            background: #474747;
        }
        footer {
            display: none!important;
        }
        .q-pa-md {
            padding: 4px 4px!important;
        }
        input[type="number"]::-webkit-inner-spin-button,
        input[type="number"]::-webkit-outer-spin-button {
            -webkit-appearance: none;
            margin: 0;
        }
        /* Firefox */
        input[type="number"] {
            -moz-appearance: textfield;
        }
        .q-card.q-card--dark {
            padding-left: 4px;
            padding-right: 4px;
        }
        .q-bar--standard {
            height: fit-content; 
        }
        .text-negative > div > i {
            display: none;
        }
        .grecaptcha-badge {
            z-index: -1!important;
        }
    `;

  // Create a style element and append it to the document
  const style = document.createElement("style");
  style.textContent = customCSS;
  document.head.appendChild(style);

  console.log("Custom CSS injected");
});
