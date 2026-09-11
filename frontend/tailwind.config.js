/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {
    colors: { slate: { 50: "#f8f8fa", 100: "#f0f0f3", 200: "#e1e1e7", 300: "#c2c2cc", 400: "#74747e", 500: "#666671", 600: "#51515c", 700: "#3f3f49", 800: "#2c2c35", 900: "#1c1c22" }, ink: "#171719", evergreen: "#252528", mint: "#f0f1f3", sand: "#f6f6f8", coral: "#485469" },
    fontFamily: { sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Arial', 'sans-serif'], serif: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Arial', 'sans-serif'] },
    boxShadow: { soft: "0 2px 6px rgba(0,0,0,0.025)" },
  } }, plugins: [],
};
