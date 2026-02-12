import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
    apiKey: "AIzaSyBY404ncB7dQ1jWEfOc8gRg8-sOsVDUQ9g",
    authDomain: "vibe-9658c.firebaseapp.com",
    projectId: "vibe-9658c",
    storageBucket: "vibe-9658c.firebasestorage.app",
    messagingSenderId: "950617225368",
    appId: "1:950617225368:web:5479b81e2c0ee61322f8ed",
    measurementId: "G-59YFM08HGD"
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
