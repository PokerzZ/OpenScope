
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GitBranch, User, Cpu, FileText, CheckCircle, ArrowRight } from 'lucide-react';

const NodeCard = ({ node, onClick, isSelected }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={() => onClick(node)}
            className={`
                relative p-4 rounded-xl border-2 transition-all cursor-pointer mb-4
                ${isSelected 
                    ? 'border-blue-500 bg-blue-50 shadow-lg scale-[1.02]' 
                    : 'border-white bg-white shadow-sm hover:border-blue-200 hover:shadow-md'
                }
            `}
        >
            <div className="flex items-center justify-between mb-2">
                <span className={`
                    text-xs font-bold px-2 py-1 rounded-full
                    ${node.type === 'START' ? 'bg-green-100 text-green-700' : 
                      node.type === 'SPLIT_START' ? 'bg-purple-100 text-purple-700' :
                      'bg-gray-100 text-gray-700'}
                `}>
                    {node.type}
                </span>
                <span className="text-xs text-gray-400">
                    {new Date(node.timestamp).toLocaleTimeString()}
                </span>
            </div>

            {node.agent && (
                <div className="flex items-center text-sm font-medium text-gray-800 mb-1">
                    <User className="w-4 h-4 mr-2 text-blue-500" />
                    {node.agent}
                </div>
            )}
            
            <div className="text-xs text-gray-500 font-mono bg-gray-50 p-2 rounded truncate">
                {node.label || node.action || 'Initializing...'}
            </div>

            {node.status === 'completed' && (
                <div className="absolute -right-2 -top-2 bg-green-500 rounded-full p-1 border-2 border-white">
                    <CheckCircle className="w-3 h-3 text-white" />
                </div>
            )}
        </motion.div>
    );
};

export const GraphView = ({ nodes, paths, onNodeSelect, selectedNodeId }) => {
    // Group nodes by Path ID
    const pathGroups = Object.keys(paths).reduce((acc, pathId) => {
        acc[pathId] = nodes.filter(n => n.pathId === pathId);
        return acc;
    }, {});

    return (
        <div className="h-full overflow-x-auto overflow-y-hidden bg-gray-50/50 p-6">
            <div className="flex space-x-8 min-w-max h-full">
                {Object.entries(pathGroups).map(([pathId, pathNodes]) => (
                    <div 
                        key={pathId} 
                        className="w-80 flex-shrink-0 flex flex-col h-full"
                    >
                        {/* Column Header */}
                        <div className="bg-white p-4 rounded-t-xl border border-gray-200 shadow-sm mb-4 sticky top-0 z-10">
                            <div className="flex items-center justify-between mb-2">
                                <h3 className="font-bold text-gray-800 flex items-center">
                                    <GitBranch className="w-4 h-4 mr-2 text-purple-600" />
                                    Path {pathId}
                                </h3>
                                <div className="flex items-center text-xs space-x-2">
                                    <span className={`w-2 h-2 rounded-full ${
                                        paths[pathId].status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
                                    }`} />
                                    <span className="text-gray-500 capitalize">{paths[pathId].status}</span>
                                </div>
                            </div>
                            {paths[pathId].parentId && (
                                <div className="text-xs text-purple-600 flex items-center bg-purple-50 px-2 py-1 rounded">
                                    <ArrowRight className="w-3 h-3 mr-1" />
                                    Split from Path {paths[pathId].parentId}
                                </div>
                            )}
                        </div>

                        {/* Nodes Container */}
                        <div className="flex-1 overflow-y-auto pb-20 custom-scrollbar pr-2">
                            <div className="relative">
                                {/* Vertical Line */}
                                <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-200 -ml-[1px]" />
                                
                                {pathNodes.map((node) => (
                                    <NodeCard 
                                        key={node.id} 
                                        node={node} 
                                        onClick={onNodeSelect}
                                        isSelected={selectedNodeId === node.id}
                                    />
                                ))}
                            </div>
                        </div>
                    </div>
                ))}
                
                {Object.keys(paths).length === 0 && (
                    <div className="flex items-center justify-center w-full h-full text-gray-400">
                        <div className="text-center">
                            <Cpu className="w-12 h-12 mx-auto mb-4 opacity-20" />
                            <p>Waiting for agent reasoning paths...</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
