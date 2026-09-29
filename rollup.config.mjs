// SPDX-License-Identifier: MIT
// Copyright (c) 2026 GPD5CachyAutoTDP Contributors
import typescript from "@rollup/plugin-typescript";
import commonjs from "@rollup/plugin-commonjs";
import resolve from "@rollup/plugin-node-resolve";

export default {
  input: "src/index.tsx",
  output: {
    file: "dist/index.js",
    format: "iife",
    exports: "default",
    name: "AutoTDP_Plugin",
    globals: {
      react: "SP_REACT",
      "react-dom": "SP_REACTDOM",
      "react/jsx-runtime": "SP_REACT",
      "@decky/ui": "DFL",
      "@decky/api": "DFL"
    },
    intro: "",
    outro: ""
  },
  external: ["react", "react-dom", "react/jsx-runtime", "@decky/ui", "@decky/api"],
  plugins: [
    resolve({browser:true, preferBuiltins:false}),
    commonjs(),
    typescript({tsconfig:"./tsconfig.json"})
  ],
  onwarn(warning, warn) {
    if (warning.code === "THIS_IS_UNDEFINED" && warning.id?.includes("@decky")) return;
    warn(warning);
  }
};
