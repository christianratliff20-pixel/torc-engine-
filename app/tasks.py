import React, { useState } from 'react';
import { 
  Phone, AlertTriangle, Edit3, Trash2, 
  History, Activity, ShieldAlert,
  MessageSquare, Sun, Moon, CheckCircle2,
  Radio, Clock, ArrowUpRight
} from 'lucide-react';

// --- TYPES ---
interface ActionTicketData {
  id: string;
  callId: string;
  status: 'OPEN' | 'IN_PROGRESS' | 'RESOLVED';
  aiReasoning: string;
  summary: string;
  assignedRole: string;
  isEdited: boolean;
  lastEditedBy?: string;
  lastEditedAt?: string;
}

interface ActivityLogItem {
  id: string;
  timestamp: string;
  callerName: string;
  orgName: string;
  eventType: 'INBOUND_CALL' | 'OUTBOUND_DISPATCH' | 'TICKET_CREATED';
  duration?: string;
  transcriptPreview: string;
  ticket?: ActionTicketData;
}

export const AnkoraCommandCenter: React.FC = () => {
  // Theme State (Local to component for easy testing)
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const isDark = theme === 'dark';

  // Active Navigation State
  const [activeTab, setActiveTab] = useState<'LIVE' | 'TIMELINE'>('LIVE');
  const [selectedLogId, setSelectedLogId] = useState<string>('log-1');
  
  // Action Ticket Edit State
  const [isEditingTicket, setIsEditingTicket] = useState(false);
  const [ticketReasoning, setTicketReasoning] = useState(
    "Caller requested emergency plumbing dispatch. Customer mentioned active water leak in commercial unit."
  );
  const [ticketSummary, setTicketSummary] = useState(
    "Dispatch On-Call Technician to 452 Industrial Pkwy immediately."
  );

  // Mock Activity Feed
  const logs: ActivityLogItem[] = [
    {
      id: 'log-1',
      timestamp: '10:42:15 AM',
      callerName: 'Sarah Jenkins',
      orgName: 'Apex Logistics Corp',
      eventType: 'INBOUND_CALL',
      duration: '3m 12s',
      transcriptPreview: "We need someone out here right now, the main line is backing up into the warehouse...",
      ticket: {
        id: 'TCK-8821',
        callId: 'call-901',
        status: 'OPEN',
        aiReasoning: "Caller requested emergency plumbing dispatch. Customer mentioned active water leak in commercial unit.",
        summary: "Dispatch On-Call Technician to 452 Industrial Pkwy immediately.",
        assignedRole: "Dispatch Lead",
        isEdited: true,
        lastEditedBy: "Admin (You)",
        lastEditedAt: "10:44 AM"
      }
    },
    {
      id: 'log-2',
      timestamp: '09:15:00 AM',
      callerName: 'Marcus Vance',
      orgName: 'Vance & Associates',
      eventType: 'INBOUND_CALL',
      duration: '1m 45s',
      transcriptPreview: "Just calling to confirm if our billing statement was processed for July...",
      ticket: {
        id: 'TCK-8819',
        callId: 'call-899',
        status: 'RESOLVED',
        aiReasoning: "Standard balance inquiry. AI retrieved balance ($120.00) via background database query.",
        summary: "Billing statement confirmed sent via email.",
        assignedRole: "Automated AI",
        isEdited: false
      }
    }
  ];

  const selectedLog = logs.find(l => l.id === selectedLogId) || logs[0];

  // Dynamic Theme Styling Helper
  const t = {
    bgMain: isDark ? 'bg-[#0A0D14]' : 'bg-[#F8FAFC]',
    bgSurface: isDark ? 'bg-[#121824]' : 'bg-[#FFFFFF]',
    bgCardHover: isDark ? 'hover:bg-[#182030]' : 'hover:bg-slate-50',
    border: isDark ? 'border-slate-800' : 'border-slate-200',
    borderActive: isDark ? 'border-[#FF5722]' : 'border-[#FF5722]',
    textPrimary: isDark ? 'text-slate-100' : 'text-slate-900',
    textSecondary: isDark ? 'text-slate-400' : 'text-slate-500',
    textMuted: isDark ? 'text-slate-500' : 'text-slate-400',
    inputBg: isDark ? 'bg-[#0A0D14]' : 'bg-slate-50',
  };

  return (
    <div className={`flex h-screen ${t.bgMain} ${t.textPrimary} font-sans overflow-hidden transition-colors duration-200`}>
      
      {/* 1. LEFT PANE: WORKSPACE & ORGANIZATION TREE */}
      <div className={`w-64 border-r ${t.border} ${t.bgSurface} flex flex-col justify-between`}>
        <div>
          {/* Workspace Brand Header */}
          <div className={`p-4 border-b ${t.border} flex items-center justify-between`}>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-[#FF5722] rounded-md flex items-center justify-center font-bold text-xs text-white tracking-wider shadow-sm">
                AK
              </div>
              <div>
                <span className="font-semibold text-sm block leading-tight">Ankora Enterprise</span>
                <span className={`text-[10px] ${t.textMuted} font-mono`}>COMMAND CENTER</span>
              </div>
            </div>

            {/* Theme Toggle Button */}
            <button
              onClick={() => setTheme(isDark ? 'light' : 'dark')}
              className={`p-1.5 rounded-md border ${t.border} ${t.bgMain} ${t.textSecondary} hover:text-[#FF5722] transition-colors`}
              title={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
            >
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
          </div>

          {/* Navigation Matrix */}
          <div className="p-3 space-y-1.5">
            <button 
              onClick={() => setActiveTab('LIVE')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-all ${
                activeTab === 'LIVE' 
                  ? 'bg-[#FF5722]/15 text-[#FF5722] border border-[#FF5722]/30 font-semibold' 
                  : `${t.textSecondary} ${t.bgCardHover}`
              }`}
            >
              <div className="flex items-center gap-2">
                <Phone className="w-4 h-4" />
                <span>Live Switchboard</span>
              </div>
              <span className="w-2 h-2 rounded-full bg-[#00F2FE] animate-pulse shadow-[0_0_8px_#00F2FE]"></span>
            </button>

            <button 
              onClick={() => setActiveTab('TIMELINE')}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-md text-sm font-medium transition-all ${
                activeTab === 'TIMELINE' 
                  ? 'bg-[#FF5722]/15 text-[#FF5722] border border-[#FF5722]/30 font-semibold' 
                  : `${t.textSecondary} ${t.bgCardHover}`
              }`}
            >
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4" />
                <span>Master Activity Log</span>
              </div>
            </button>
          </div>
        </div>

        {/* Telephony & Infrastructure Status Footer */}
        <div className={`p-4 border-t ${t.border} text-xs ${t.textSecondary} flex flex-col gap-1.5`}>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-[#00F2FE]" /> WebRTC Engine
            </span>
            <span className="text-[#00F2FE] font-mono text-[11px] font-semibold">CONNECTED</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="flex items-center gap-1.5">
              <Clock className="w-3 h-3" /> STT Latency
            </span>
            <span className={`font-mono text-[11px] ${t.textPrimary}`}>118ms</span>
          </div>
        </div>
      </div>

      {/* 2. CENTER PANE: THE LIVING TIMELINE & STREAM */}
      <div className={`flex-1 flex flex-col ${t.bgMain} border-r ${t.border}`}>
        {/* Header */}
        <div className={`p-4 border-b ${t.border} flex justify-between items-center ${t.bgSurface}`}>
          <div>
            <h1 className={`text-base font-semibold ${t.textPrimary}`}>
              {activeTab === 'LIVE' ? 'Live Telephony Stream' : 'Organization Master Feed'}
            </h1>
            <p className={`text-xs ${t.textSecondary}`}>
              {activeTab === 'LIVE' 
                ? 'Monitoring real-time caller audio tracks & prompt execution' 
                : 'Cross-channel timeline of events, calls, and dispatch tickets'}
            </p>
          </div>
          {activeTab === 'LIVE' && (
            <button className="bg-[#FF5722] hover:bg-[#E64A19] text-white px-3.5 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all shadow-sm">
              <ShieldAlert className="w-3.5 h-3.5" />
              Barge-In (Human Takeover)
            </button>
          )}
        </div>

        {/* Log/Stream List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {logs.map((log) => {
            const isSelected = selectedLogId === log.id;
            return (
              <div 
                key={log.id}
                onClick={() => setSelectedLogId(log.id)}
                className={`p-4 rounded-lg border transition-all cursor-pointer ${
                  isSelected 
                    ? `${t.bgSurface} border-[#FF5722] shadow-md ring-1 ring-[#FF5722]/30` 
                    : `${t.bgSurface}/60 ${t.border} ${t.bgCardHover}`
                }`}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold ${t.textPrimary} text-sm`}>{log.callerName}</span>
                    <span className="text-xs text-slate-500">•</span>
                    <span className={`text-xs font-mono ${t.textSecondary}`}>{log.orgName}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-xs ${t.textMuted} font-mono`}>{log.timestamp}</span>
                    {log.ticket && (
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        log.ticket.status === 'OPEN' 
                          ? 'bg-[#FF5722]/15 border-[#FF5722]/40 text-[#FF5722]' 
                          : 'bg-emerald-500/15 border-emerald-500/40 text-emerald-500'
                      }`}>
                        {log.ticket.status}
                      </span>
                    )}
                  </div>
                </div>

                {/* Transcript Snippet */}
                <p className={`text-xs ${t.textPrimary} font-mono ${t.inputBg} p-3 rounded-md border ${t.border} mb-3 leading-relaxed`}>
                  "{log.transcriptPreview}"
                </p>

                {/* Contextual Action Menu */}
                <div className={`flex justify-between items-center text-xs border-t ${t.border} pt-2.5`}>
                  <span className={`${t.textMuted} text-[11px]`}>Duration: {log.duration}</span>
                  <div className={`flex gap-4 ${t.textSecondary}`}>
                    <button className="hover:text-[#FF5722] flex items-center gap-1 transition-colors">
                      <MessageSquare className="w-3 h-3" /> Raw Transcript
                    </button>
                    <button className="hover:text-[#FF5722] flex items-center gap-1 transition-colors">
                      <Edit3 className="w-3 h-3" /> Correct Logic
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. RIGHT PANE: ACTION TICKET & AUDIT DRAWER */}
      <div className={`w-96 border-l ${t.border} ${t.bgSurface} flex flex-col`}>
        <div className={`p-4 border-b ${t.border} flex justify-between items-center`}>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#FF5722]" />
            <h2 className={`text-sm font-semibold ${t.textPrimary}`}>Action Ticket Control</h2>
          </div>
          <span className={`text-xs font-mono ${t.textMuted}`}>{selectedLog.ticket?.id || 'NO TICKET'}</span>
        </div>

        {selectedLog.ticket ? (
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            
            {/* AI Reasoning Block */}
            <div className={`p-3.5 rounded-lg border ${t.border} ${t.bgMain}`}>
              <span className={`text-[11px] font-semibold ${t.textSecondary} tracking-wider uppercase block mb-1.5`}>
                AI Reasoning Trace
              </span>
              {isEditingTicket ? (
                <textarea 
                  value={ticketReasoning}
                  onChange={(e) => setTicketReasoning(e.target.value)}
                  className={`w-full ${t.inputBg} border ${t.border} text-xs ${t.textPrimary} p-2.5 rounded focus:outline-none focus:border-[#FF5722] font-mono h-20 resize-none`}
                />
              ) : (
                <p className={`text-xs ${t.textPrimary} font-mono leading-relaxed`}>
                  {ticketReasoning}
                </p>
              )}
            </div>

            {/* Generated Action Payloads */}
            <div className={`p-3.5 rounded-lg border ${t.border} ${t.bgMain}`}>
              <span className={`text-[11px] font-semibold ${t.textSecondary} tracking-wider uppercase block mb-1.5`}>
                Instruction / Ticket Action
              </span>
              {isEditingTicket ? (
                <textarea 
                  value={ticketSummary}
                  onChange={(e) => setTicketSummary(e.target.value)}
                  className={`w-full ${t.inputBg} border ${t.border} text-xs ${t.textPrimary} p-2.5 rounded focus:outline-none focus:border-[#FF5722] font-mono h-20 resize-none`}
                />
              ) : (
                <p className={`text-xs ${t.textPrimary} font-mono leading-relaxed`}>
                  {ticketSummary}
                </p>
              )}
            </div>

            {/* Control Actions */}
            <div className="pt-2 space-y-2">
              {isEditingTicket ? (
                <div className="flex gap-2">
                  <button 
                    onClick={() => setIsEditingTicket(false)}
                    className="flex-1 bg-[#FF5722] hover:bg-[#E64A19] text-white py-2 rounded-md text-xs font-semibold transition-all shadow-sm"
                  >
                    Save & Update Audit Log
                  </button>
                  <button 
                    onClick={() => setIsEditingTicket(false)}
                    className={`bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-2 rounded-md text-xs font-semibold`}
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button 
                    onClick={() => setIsEditingTicket(true)}
                    className={`flex-1 ${t.bgMain} hover:border-[#FF5722] border ${t.border} ${t.textPrimary} py-2 rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition-all`}
                  >
                    <Edit3 className="w-3.5 h-3.5 text-[#FF5722]" /> Edit / Override Ticket
                  </button>
                  <button className="bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 text-red-500 px-3 py-2 rounded-md text-xs font-semibold transition-all">
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>

            {/* Strict Audit Trail Footer */}
            {selectedLog.ticket.isEdited && (
              <div className={`mt-4 p-3 ${t.bgMain} rounded-md border ${t.border} text-[11px] space-y-1`}>
                <div className="flex items-center gap-1.5 text-[#FF5722] font-semibold">
                  <History className="w-3.5 h-3.5" />
                  <span>Audit History Recorded</span>
                </div>
                <div className={t.textSecondary}>
                  Modified by <span className={`font-semibold ${t.textPrimary}`}>{selectedLog.ticket.lastEditedBy}</span>
                </div>
                <div className={`${t.textMuted} font-mono text-[10px]`}>
                  Timestamp: {selectedLog.ticket.lastEditedAt}
                </div>
              </div>
            )}

          </div>
        ) : (
          <div className={`flex-1 flex items-center justify-center p-6 text-center ${t.textMuted} text-xs`}>
            Select a log entry with an associated Action Ticket to view details.
          </div>
        )}
      </div>

    </div>
  );
};
