// Initialize Firebase
const firebaseConfig = {
  apiKey: "AIzaSyCt_Nk7OK8ZrSourN0VffWnFoNO6l_NopY",
  authDomain: "task-management-system-a66d0.firebaseapp.com",
  projectId: "task-management-system-a66d0",
  storageBucket: "task-management-system-a66d0.firebasestorage.app",
  messagingSenderId: "414442292882",
  appId: "1:414442292882:web:6b620dcd66eb4c58e7c84b",
};

firebase.initializeApp(firebaseConfig);

// Set persistence to LOCAL (persists even when browser is closed)
firebase
  .auth()
  .setPersistence(firebase.auth.Auth.Persistence.LOCAL)
  .catch((error) => {
    console.error("Persistence error:", error);
  });

// Check auth state on page load
firebase.auth().onAuthStateChanged((user) => {
  if (user && window.location.pathname === "/") {
    // User is signed in and on login page, redirect to boards
    window.location.href = "/boards";
  }
});

// After successful login, send the token to the server
async function sendTokenToServer(user) {
  const token = await user.getIdToken();

  await fetch("/api/set-auth-cookie", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ token }),
  });
}

// Login function
function login() {
  const email = document.getElementById("email").value;
  const password = document.getElementById("password").value;

  firebase
    .auth()
    .signInWithEmailAndPassword(email, password)
    .then((userCredential) => {
      sendTokenToServer(userCredential.user).then(
        () => (window.location.href = "/boards")
      );
    })
    .catch((err) => {
      console.log(err);
      // Extract the actual error message
      let errorMessage = "Login failed";

      if (err.message) {
        // Parse the JSON error message if it exists
        try {
          const parsedError = JSON.parse(err.message);
          if (parsedError.error && parsedError.error.message) {
            errorMessage = parsedError.error.message;
          }
        } catch (e) {
          // Use the original message incase parsing fails
          errorMessage = err.message;
        }
      }

      alert("Error: " + errorMessage);
    });
}

// Update Google sign-in function
function handleGoogleSignin() {
  firebase
    .auth()
    .signInWithPopup(new firebase.auth.GoogleAuthProvider())
    .then((result) => {
      sendTokenToServer(result.user).then(
        () => (window.location.href = "/boards")
      );
    })
    .catch((error) => {
      console.log(error);
    });
}

// Also handle token on page load for existing sessions
firebase.auth().onAuthStateChanged((user) => {
  if (user) {
    // User is signed in
    sendTokenToServer(user).then(() => {
      if (window.location.pathname === "/") {
        window.location.href = "/boards";
      }
    });
  }
});

// Get User profile
async function getUserProfile() {
  const user = firebase.auth().currentUser;
  if (!user) return null;
  
  try {
    // Force refresh to get the latest user data
    await user.reload();
    
    return {
      uid: user.uid,
      email: user.email,
      displayName: user.displayName,
      emailVerified: user.emailVerified,
      photoURL: user.photoURL,
      createdAt: user.metadata.creationTime,
      lastLogin: user.metadata.lastSignInTime
    };
  } catch (error) {
    console.error("Error getting user profile:", error);
    return null;
  }
}

// Function to handle password reset
function resetPassword() {
  const email = document.getElementById('email').value.trim();
  
  if (!email) {
    alert('Please enter your email address');
    return;
  }
  
  // Configure action code settings
  const actionCodeSettings = {
    // URL you want to redirect back to after password reset
    url: window.location.origin + '/',
    handleCodeInApp: true
  };
  
  firebase.auth().sendPasswordResetEmail(email, actionCodeSettings)
    .then(() => {
      // Show success message
      document.getElementById('success-message').classList.remove('hidden');
      // Clear the form
      document.getElementById('email').value = '';
    })
    .catch((error) => {
      console.error('Password reset error:', error);
      alert(`Password reset failed: ${error.message}`);
    });
}
