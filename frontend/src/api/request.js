import axios from "axios";

const request = axios.create({
  // Use same-origin requests in dev and rely on Vite proxy.
  // This avoids CORS/mixed-content issues in remote forwarding scenarios.
  baseURL: "/",
  timeout: 600000
});

export default request;
