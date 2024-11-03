import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        gold: "#D4AF37",
        navy: "#003366",
      },
      width: {
        'icon': '20rem',
      },
      height: {
        'icon': '20rem',
      }
    },
  },
  plugins: [],
};
export default config;
