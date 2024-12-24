import axios from "axios";

const API_ADDRESS = process.env.REACT_APP_API_ADDRESS;

export default axios.create({
  baseURL: `${API_ADDRESS}`,
  headers: {
    "Content-type": "application/json",
  },
});
