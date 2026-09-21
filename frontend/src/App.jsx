import { useState } from "react";
import Dashboard from "./Dashboard.jsx";
import AuthScreen from "./AuthScreen.jsx";

function App() {
  const [token, setToken] = useState(() => {
    try { return localStorage.getItem("token"); } catch (e) { return null; }
  });

  const handleAuthenticated = (newToken) => {
    try { localStorage.setItem("token", newToken); } catch (e) {}
    setToken(newToken);
  };

  const handleLogout = () => {
    try { localStorage.removeItem("token"); } catch (e) {}
    setToken(null);
  };

  return token
    ? <Dashboard token={token} onLogout={handleLogout} />
    : <AuthScreen onAuthenticated={handleAuthenticated} />;
}

export default App;
