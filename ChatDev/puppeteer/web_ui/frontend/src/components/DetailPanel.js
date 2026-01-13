
import React from 'react';
import { X, FileCode, MessageSquare, Database } from 'lucide-react';

export const DetailPanel = ({ node, onClose }) => {
    if (!node) return null;

    return (
        <div className="fixed inset-y-0 right-0 w-[500px] bg-white shadow-2xl border-l border-gray-200 z-50 flex flex-col transform transition-transform">
            {/* Header */}
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <div>
                    <h2 className="text-lg font-bold text-gray-900 flex items-center">
                        <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs mr-2">
                            {node.type}
                        </span>
                        Node Details
                    </h2>
                    <p className="text-xs text-gray-500 font-mono mt-1">{node.id}</p>
                </div>
                <button 
                    onClick={onClose}
                    className="p-2 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Agent Info */}
                {node.agent && (
                    <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                            <Database className="w-4 h-4 mr-2" />
                            Agent Context
                        </h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs text-gray-400 uppercase tracking-wider">Agent Name</label>
                                <p className="font-medium text-gray-900">{node.agent}</p>
                            </div>
                            <div>
                                <label className="text-xs text-gray-400 uppercase tracking-wider">Action</label>
                                <p className="font-medium text-gray-900">{node.action}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Query/Input */}
                {node.data?.query && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                            <FileCode className="w-4 h-4 mr-2" />
                            Model Query
                        </h3>
                        <div className="bg-gray-900 rounded-xl p-4 overflow-x-auto">
                            <pre className="text-sm text-gray-300 font-mono whitespace-pre-wrap">
                                {typeof node.data.query === 'object' 
                                    ? JSON.stringify(node.data.query, null, 2)
                                    : node.data.query}
                            </pre>
                        </div>
                    </div>
                )}

                {/* Response/Reasoning */}
                {node.data?.parse && (
                    <div>
                        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                            <MessageSquare className="w-4 h-4 mr-2" />
                            Reasoning / Response
                        </h3>
                        <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
                            <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                                {typeof node.data.parse === 'object'
                                    ? JSON.stringify(node.data.parse, null, 2)
                                    : node.data.parse}
                            </p>
                        </div>
                    </div>
                )}
                
                {/* Raw Dump (Debug) */}
                 <div className="border-t pt-4 mt-8">
                    <details>
                        <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">Raw Details JSON</summary>
                        <pre className="mt-2 text-[10px] text-gray-400 overflow-x-auto bg-gray-50 p-2 rounded">
                            {JSON.stringify(node, null, 2)}
                        </pre>
                    </details>
                </div>
            </div>
        </div>
    );
};
