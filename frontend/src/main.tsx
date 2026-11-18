import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import FlowsteadApp from './app/App';
import './styles.css';

createRoot(document.getElementById('root')!).render(<StrictMode><FlowsteadApp /></StrictMode>);
