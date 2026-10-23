import React from 'react';
import { Clock, UserCheck, CheckCircle2, PackageCheck, XCircle } from 'lucide-react';

export default function StatusBadge({ status }) {
  const normalized = status ? status.toUpperCase() : 'PENDING';

  switch (normalized) {
    case 'PENDING':
      return (
        <span className="badge badge-pending">
          <Clock size={12} /> Pending
        </span>
      );
    case 'ASSIGNED':
      return (
        <span className="badge badge-assigned">
          <UserCheck size={12} /> Assigned
        </span>
      );
    case 'ACCEPTED':
      return (
        <span className="badge badge-accepted">
          <CheckCircle2 size={12} /> Accepted
        </span>
      );
    case 'PICKED_UP':
      return (
        <span className="badge badge-picked_up">
          <PackageCheck size={12} /> Picked Up
        </span>
      );
    case 'CANCELLED':
      return (
        <span className="badge badge-cancelled">
          <XCircle size={12} /> Cancelled
        </span>
      );
    default:
      return <span className="badge">{status}</span>;
  }
}
