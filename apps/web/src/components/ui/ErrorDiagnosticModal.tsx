"use client";

import React, { useState } from 'react';
import { AlertTriangle, ChevronDown, ChevronUp, RefreshCw, X } from 'lucide-react';

interface ErrorDiagnosticModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRetry?: () => void;
  title?: string;
  userMessage: string;
  technicalError?: string | null;
  errorCode?: string | null;
  requestId?: string | null;
}

export const ErrorDiagnosticModal: React.FC<ErrorDiagnosticModalProps> = ({
  isOpen,
  onClose,
  onRetry,
  title = "Action Failed",
  userMessage,
  technicalError,
  errorCode = "SYSTEM_ERROR",
  requestId
}) => {
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-[#11141D] border border-rose-500/30 rounded-2xl max-w-lg w-full p-6 shadow-2xl shadow-rose-950/20 text-white relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white p-1 rounded-lg hover:bg-[#1A1F2C] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-start gap-4">
          <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 shrink-0">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div className="space-y-1">
            <h3 className="text-lg font-bold text-white">{title}</h3>
            <p className="text-sm text-gray-300 leading-relaxed">{userMessage}</p>
          </div>
        </div>

        {/* Technical Diagnostics Accordion */}
        {technicalError && (
          <div className="mt-5 border-t border-[#1F2937] pt-4">
            <button
              onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              className="flex items-center justify-between w-full text-xs font-medium text-gray-400 hover:text-gray-200 py-1"
            >
              <span>Technical Diagnostics ({errorCode})</span>
              {showTechnicalDetails ? (
                <ChevronUp className="w-4 h-4 text-gray-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-400" />
              )}
            </button>

            {showTechnicalDetails && (
              <div className="mt-2 p-3 bg-[#0B0D12] border border-[#1F2937] rounded-xl text-xs font-mono text-rose-300 space-y-2 overflow-x-auto">
                {requestId && (
                  <div>
                    <span className="text-gray-500">Request ID:</span> {requestId}
                  </div>
                )}
                <div>
                  <span className="text-gray-500">Error Code:</span> {errorCode}
                </div>
                <div className="text-gray-300 whitespace-pre-wrap max-h-36 overflow-y-auto">
                  {technicalError}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-6 flex items-center justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-gray-400 hover:text-white rounded-xl hover:bg-[#1A1F2C] transition-colors"
          >
            Dismiss
          </button>
          {onRetry && (
            <button
              onClick={() => {
                onClose();
                onRetry();
              }}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-all shadow-md shadow-indigo-600/20"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry Action</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
