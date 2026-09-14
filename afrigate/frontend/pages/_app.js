import "../styles/globals.css";
import { AuthProvider } from "../lib/auth-context";
import AuthModal from "../components/AuthModal";

export default function App({ Component, pageProps }) {
  return (
    <AuthProvider>
      <Component {...pageProps} />
      <AuthModal />
    </AuthProvider>
  );
}
