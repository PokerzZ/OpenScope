
import React, { useReducer, useEffect, useRef, useState } from 'react';
import { Play, Activity, Terminal, Layout, Cpu } from 'lucide-react';
import { parseLogMessage } from './lib/parser';
import { graphReducer, initialState } from './lib/reducer';
import { GraphView } from './components/GraphView';
import { DetailPanel } from './components/DetailPanel';
import { LogsView } from './components/LogsView';

const App = () => {
    // State Management
    const [state, dispatch] = useReducer(graphReducer, initialState);
    const [selectedNode, setSelectedNode] = useState(null);
    const [showLogs, setShowLogs] = useState(true);
    const ws = useRef(null);

    // Initial Load & Persistence
    useEffect(() => {
        const savedRepo = localStorage.getItem('puppeteer_repoName');
        if (savedRepo) {
            dispatch({ type: 'UPDATE_REPO', repoName: savedRepo });
        }
    }, []);

    // WebSocket Logic
    useEffect(() => {
        const connect = () => {
            ws.current = new WebSocket('ws://localhost:8000/ws');
            
            ws.current.onopen = () => {
                console.log('WS Connected');
            };

            ws.current.onmessage = (event) => {
                try {
                    const rawData = JSON.parse(event.data);
                    
                    const parsedEvent = parseLogMessage(rawData);
                    
                    dispatch({ 
                        type: 'LOG', 
                        content: rawData.message || JSON.stringify(rawData), 
                        timestamp: rawData.timestamp || Date.now()
                    });

                    if (parsedEvent) {
                        dispatch(parsedEvent);
                    }
                } catch (e) {
                    // Fallback for non-JSON messages if any 
                     dispatch({ type: 'LOG', content: event.data, timestamp: Date.now() });
                }
            };

            ws.current.onclose = () => {
                setTimeout(connect, 3000); 
            };
        };

        connect();
        return () => ws.current?.close();
    }, []);

    const handleStart = () => {
        if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
            alert('Backend not connected');
            return;
        }
        dispatch({ type: 'START_INFERENCE' });
        ws.current.send(JSON.stringify({
            action: 'start_inference',
            repo_name: state.repoName
        }));
    };

    const handleRepoChange = (e) => {
        const newName = e.target.value;
        dispatch({ type: 'UPDATE_REPO', repoName: newName });
        localStorage.setItem('puppeteer_repoName', newName);
    };

    return (
        <div className="flex h-screen bg-gray-100 font-sans text-gray-900 overflow-hidden">
            
            {/* Sidebar (Controls & Logs) */}
            <div className={`${showLogs ? 'w-80' : 'w-16'} bg-gray-900 flex-shrink-0 flex flex-col transition-all duration-300 border-r border-gray-800`}>
                <div className="p-4 flex items-center justify-between border-b border-gray-800 h-16">
                    {showLogs && <h1 className="text-white font-bold text-lg tracking-tight">Puppeteer</h1>}
                    <button onClick={() => setShowLogs(!showLogs)} className="text-gray-400 hover:text-white">
                        <Layout className="w-5 h-5" />
                    </button>
                </div>

                {showLogs ? (
                    <>
                        <div className="p-4 space-y-4">
                            <div>
                                <label className="text-xs text-gray-500 uppercase font-bold block mb-1">Target Repo</label>
                                <input 
                                    className="w-full bg-gray-800 text-white border-0 rounded p-2 text-sm focus:ring-1 focus:ring-blue-500 placeholder-gray-500"
                                    value={state.repoName}
                                    onChange={handleRepoChange}
                                    placeholder="owner/repo"
                                /> 
                            </div>
                            <button 
                                onClick={handleStart}
                                disabled={state.status === 'inferencing'}
                                className={`
                                    w-full py-3 rounded-lg font-bold text-sm tracking-wide transition-all flex items-center justify-center
                                    ${state.status === 'inferencing' 
                                        ? 'bg-yellow-600 text-white cursor-wait opacity-80' 
                                        : 'bg-blue-600 hover:bg-blue-500 text-white shadow-lg transform hover:-translate-y-0.5'}
                                `}
                            >
                                {state.status === 'inferencing' ? <Activity className="w-4 h-4 mr-2 animate-spin" /> : <Play className="w-4 h-4 mr-2" />}
                                {state.status === 'inferencing' ? 'REASONING...' : 'START RUN'}
                            </button>
                        </div>
                        
                        <div className="flex-1 overflow-hidden relative border-t border-gray-800">
                             <LogsView logs={state.logs} />
                        </div>
                    </>
                ) : (
                    <div className="flex flex-col items-center pt-6 space-y-6">
                        <Cpu className="text-gray-500 w-6 h-6" />
                        <button onClick={handleStart} className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white hover:bg-blue-500">
                           <Play className="w-4 h-4" />
                        </button>
                    </div>
                )}
            </div>

            {/* Main Content (Graph) */}
            <div className="flex-1 flex flex-col h-full overflow-hidden relative">
                {/* Top Bar */}
                <header className="bg-white h-16 border-b border-gray-200 flex items-center px-6 justify-between shadow-sm z-10">
                    <div className="flex items-center text-sm breadcrumbs text-gray-500">
                        <span className="font-semibold text-gray-900 mr-2">Dashboard</span>
                        {state.activePathId && (
                            <>
                                <span className="mx-2 text-gray-300">/</span>
                                <span className="bg-blue-100 text-blue-800 px-2 py-0.5 rounded-full text-xs font-mono">
                                    Path {state.activePathId}
                                </span>
                            </>
                        )}
                         {state.status === 'inferencing' && (
                             <span className="ml-4 flex items-center text-green-600 text-xs animate-pulse">
                                 <Activity className="w-3 h-3 mr-1" /> Processing
                             </span>
                         )}
                    </div>
                     <div className="flex items-center space-x-4">
                        <div className="text-xs font-mono text-gray-400 bg-gray-50 px-2 py-1 rounded">
                             {state.nodes.length} Nodes
                        </div>
                    </div>
                </header>

                {/* Graph Canvas */}
                <div className="flex-1 overflow-hidden bg-slate-50 relative">
                    <GraphView 
                        nodes={state.nodes} 
                        paths={state.paths} 
                        onNodeSelect={setSelectedNode}
                        selectedNodeId={selectedNode?.id}
                    />
                </div>
            </div>

            {/* Right Panel (Details) */}
            <DetailPanel 
                node={selectedNode} 
                onClose={() => setSelectedNode(null)} 
            />
        </div>
    );
};

export default App;
