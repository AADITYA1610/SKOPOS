import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import HomePage from "./pages/HomePage";
import AnalyzePage from "./pages/AnalyzePage";
import ResultsPage from "./pages/ResultsPage";
import VizPage from "./pages/VizPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import ActivityPage from "./pages/ActivityPage";
import LiveStreamPage from "./pages/LiveStreamPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/results" element={<ResultsPage />} />
        <Route path="/visualize" element={<VizPage />} />
        <Route path="/activity" element={<ActivityPage />} />
        <Route path="/streams" element={<LiveStreamPage />} />
      </Route>
    </Routes>
  );
}

export default App;