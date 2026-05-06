import axios from "axios";

const request = axios.create({
  baseURL: "http://localhost:8000",
  timeout: 8000
});

export default request;
