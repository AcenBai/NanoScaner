import { Navigate, Route, Routes } from "react-router-dom";
import MainLayout from "./layouts/MainLayout";
import Dashboard from "./pages/Dashboard";
import UploadSignal from "./pages/feature/UploadSignal";
import PreprocessSignal from "./pages/feature/PreprocessSignal";
import ExtractFeatures from "./pages/feature/ExtractFeatures";
import FeatureVisualization from "./pages/feature/FeatureVisualization";
import ExportFeatures from "./pages/feature/ExportFeatures";
import UploadDataset from "./pages/classifier/UploadDataset";
import TrainModel from "./pages/classifier/TrainModel";
import ModelEvaluation from "./pages/classifier/ModelEvaluation";
import OnlinePrediction from "./pages/classifier/OnlinePrediction";
import ReportPage from "./pages/classifier/ReportPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="feature/upload-signal" element={<UploadSignal />} />
        <Route path="feature/preprocess-signal" element={<PreprocessSignal />} />
        <Route path="feature/extract-features" element={<ExtractFeatures />} />
        <Route
          path="feature/feature-visualization"
          element={<FeatureVisualization />}
        />
        <Route path="feature/export-features" element={<ExportFeatures />} />
        <Route path="classifier/upload-dataset" element={<UploadDataset />} />
        <Route path="classifier/train-model" element={<TrainModel />} />
        <Route path="classifier/model-evaluation" element={<ModelEvaluation />} />
        <Route
          path="classifier/online-prediction"
          element={<OnlinePrediction />}
        />
        <Route path="classifier/report" element={<ReportPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
