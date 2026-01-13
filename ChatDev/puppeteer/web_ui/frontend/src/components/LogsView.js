
import React, { useEffect, useRef } from 'react';

export const LogsView = ({ logs }) => {
    const endRef = useRef(null);

    useEffect(() => {
        endRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    return (
        <div className="flex flex-col h-full bg-black text-green-400 font-mono text-xs p-4 overflow-hidden">
            <h3 className="text-gray-500 uppercase tracking-widest text-[10px] mb-2 font-bold border-b border-gray-800 pb-2">
                System Terminal Stream
            </h3>
            <div className="flex-1 overflow-y-auto space-y-1 custom-scrollbar">
                {logs.map((log) => (
                    <div key={log.id} className="break-all whitespace-pre-wrap hover:bg-gray-900 leading-tight py-0.5">
                        <span className="text-gray-600 mr-2">
                            [{new Date(log.timestamp).toLocaleTimeString().split(' ')[0]}]
                        </span>
                        <span className={log.type === 'ERROR' ? 'text-red-500' : 'text-gray-300'}>
                           {log.content}
                        </span>
                    </div>
                ))}
                <div ref={endRef} />
            </div>
        </div>
    );
};
