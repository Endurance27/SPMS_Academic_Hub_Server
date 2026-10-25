import re
from datetime import datetime, time
from typing import List, Dict, Any, Optional
from enum import Enum

import openpyxl
import csv
import io


class TimetableParseIssue:
    def __init__(self, row: int, severity: str, message: str):
        self.row = row
        self.severity = severity  # "error" or "warning"
        self.message = message


class TimetableParser:
    """Parser for master timetable Excel/CSV files"""
    
    WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    WEEKDAY_MAP = {d[:3].lower(): i for i, d in enumerate(WEEKDAYS)}
    
    # Period grid: index 0-11, start = (7+i):30, end = (8+i):20
    PERIODS = [
        {"index": i, "start": f"{7+i:02d}:30", "end": f"{8+i:02d}:20", "label": f"{7+i:02d}:30 – {8+i:02d}"}
        for i in range(12)
    ]
    PERIOD_START_MAP = {p["start"]: p for p in PERIODS}
    
    def __init__(self):
        self.issues: List[TimetableParseIssue] = []
        self.entries: List[Dict[str, Any]] = []
    
    def parse_file(
        self,
        file_content: bytes,
        file_type: str,
        level: int,
        semester_id: str
    ) -> Dict[str, Any]:
        """Parse uploaded timetable file"""
        self.issues = []
        self.entries = []
        
        try:
            if file_type == "xlsx":
                self._parse_excel(file_content, level)
            elif file_type == "csv":
                self._parse_csv(file_content, level)
            else:
                self.issues.append(TimetableParseIssue(0, "error", "Upload the master timetable as an Excel (.xlsx) or CSV file"))
        except Exception as e:
            self.issues.append(TimetableParseIssue(0, "error", f"File parsing error: {str(e)}"))
        
        if not self.entries and not self.issues:
            self.issues.append(TimetableParseIssue(0, "error", "The file has a header but no timetable rows"))
        
        # Calculate summary
        free_count = sum(1 for e in self.entries if e.get("is_free"))
        venues = set(e["venue_code"] for e in self.entries)
        
        return {
            "entries": self.entries,
            "issues": [
                {"row": i.row, "severity": i.severity, "message": i.message}
                for i in self.issues
            ],
            "summary": {
                "entry_count": len(self.entries),
                "free_count": free_count,
                "venue_count": len(venues),
                "level": level
            }
        }
    
    def _parse_excel(self, content: bytes, level: int):
        """Parse Excel file"""
        workbook = openpyxl.load_workbook(io.BytesIO(content))
        sheet = workbook.active
        
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            self.issues.append(TimetableParseIssue(0, "error", "The file is empty"))
            return
        
        self._process_rows(rows, level)
    
    def _parse_csv(self, content: bytes, level: int):
        """Parse CSV file"""
        text = content.decode('utf-8')
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        
        if not rows:
            self.issues.append(TimetableParseIssue(0, "error", "The file is empty"))
            return
        
        self._process_rows(rows, level)
    
    def _process_rows(self, rows: List[tuple], level: int):
        """Process parsed rows"""
        # Find header row
        header_row = None
        for i, row in enumerate(rows):
            if any(cell and str(cell).strip() for cell in row):
                header_row = i
                break
        
        if header_row is None:
            self.issues.append(TimetableParseIssue(0, "error", "No valid header found"))
            return
        
        header = [str(cell).lower().strip() if cell else "" for cell in rows[header_row]]
        
        # Validate required columns
        required = ["day", "subject", "venue"]
        time_cols = ["time", "start"]
        has_time = any(col in header for col in time_cols)
        
        missing = [col for col in required if col not in header]
        if missing:
            self.issues.append(
                TimetableParseIssue(
                    header_row + 1,
                    "error",
                    f"Missing column(s): {', '.join(missing)}. Expected Level, Day, Time, Subject, Venue"
                )
            )
            return
        
        # Get column indices
        col_map = {col: header.index(col) for col in header}
        
        # Process data rows
        for row_idx, row in enumerate(rows[header_row + 1:], start=header_row + 2):
            if not any(cell and str(cell).strip() for cell in row):
                continue
            
            entry = self._parse_row(row, col_map, level, has_time, row_idx)
            if entry:
                self.entries.append(entry)
    
    def _parse_row(
        self,
        row: tuple,
        col_map: Dict[str, int],
        level: int,
        has_time: bool,
        row_idx: int
    ) -> Optional[Dict[str, Any]]:
        """Parse a single row"""
        try:
            # Get day
            day_cell = self._get_cell(row, col_map, "day")
            day = self._parse_day(day_cell)
            if day is None:
                self.issues.append(TimetableParseIssue(row_idx, "error", f"Unknown day: {day_cell}"))
                return None
            
            # Get time/period
            if has_time:
                time_cell = self._get_cell(row, col_map, "time") or self._get_cell(row, col_map, "start")
                periods = self._parse_time(time_cell)
                if not periods:
                    self.issues.append(TimetableParseIssue(row_idx, "error", f"Invalid time: {time_cell}"))
                    return None
            else:
                return None  # Time is required
            
            # Get subject
            subject_cell = self._get_cell(row, col_map, "subject")
            if not subject_cell or not subject_cell.strip():
                self.issues.append(TimetableParseIssue(row_idx, "error", "Empty subject"))
                return None
            
            subject = self._normalize_subject(subject_cell)
            is_free = subject == "FREE"
            
            # Get venue
            venue_cell = self._get_cell(row, col_map, "venue")
            if not venue_cell or not venue_cell.strip():
                self.issues.append(TimetableParseIssue(row_idx, "error", "Empty venue"))
                return None
            
            venue_code = self._normalize_venue(venue_cell)
            
            # Check level if specified
            level_cell = self._get_cell(row, col_map, "level")
            if level_cell:
                row_level = self._extract_level(level_cell)
                if row_level and row_level != level:
                    self.issues.append(
                        TimetableParseIssue(
                            row_idx,
                            "error",
                            f"Level {row_level} does not match the selected Level {level}"
                        )
                    )
                    return None
            
            # Create entries for each period
            entries = []
            for period_idx in periods:
                entry_id = f"{level}|{day}|{period_idx}|{venue_code}|{subject}"
                entry = {
                    "level": level,
                    "day": day,
                    "period": period_idx,
                    "subject": subject,
                    "venue_code": venue_code,
                    "is_free": is_free,
                    "course_kind": self._extract_course_kind(subject) if not is_free else None
                }
                entries.append(entry)
            
            return entries[0] if len(entries) == 1 else entries
            
        except Exception as e:
            self.issues.append(TimetableParseIssue(row_idx, "error", f"Row parse error: {str(e)}"))
            return None
    
    def _get_cell(self, row: tuple, col_map: Dict[str, int], col_name: str) -> Optional[str]:
        """Get cell value by column name"""
        if col_name not in col_map:
            return None
        idx = col_map[col_name]
        if idx >= len(row):
            return None
        cell = row[idx]
        if cell is None:
            return None
        return str(cell).strip()
    
    def _parse_day(self, day_str: str) -> Optional[int]:
        """Parse day string to index (0-4)"""
        if not day_str:
            return None
        day_key = day_str[:3].lower()
        return self.WEEKDAY_MAP.get(day_key)
    
    def _parse_time(self, time_str: str) -> List[int]:
        """Parse time string to period indices"""
        if not time_str:
            return []
        
        # Extract time tokens (HH:MM format)
        time_pattern = r"\d{1,2}[:.]\d{2}"
        matches = re.findall(time_pattern, time_str)
        
        if not matches:
            return []
        
        start_str = matches[0].replace(".", ":")
        end_str = matches[1].replace(".", ":") if len(matches) > 1 else None
        
        # Find start period
        start_period = None
        for period in self.PERIODS:
            if period["start"] == start_str:
                start_period = period["index"]
                break
        
        if start_period is None:
            return []
        
        # Find end period if specified
        if end_str:
            end_period = None
            for period in self.PERIODS:
                if period["end"] == end_str:
                    end_period = period["index"]
                    break
            if end_period is not None and end_period >= start_period:
                return list(range(start_period, end_period + 1))
        
        return [start_period]
    
    def _normalize_subject(self, subject: str) -> str:
        """Normalize subject string"""
        subject = subject.upper().strip()
        subject = re.sub(r"\s+", " ", subject)
        subject = subject.replace("©", "(C)")
        subject = re.sub(r"\(\s+C\s*\)", " (C)", subject)
        subject = re.sub(r"\(\s+E\s*\)", " (E)", subject)
        return subject
    
    def _normalize_venue(self, venue: str) -> str:
        """Normalize venue code"""
        venue = venue.upper().strip()
        venue = re.sub(r"\s+", " ", venue)
        
        # Specific normalizations
        venue = re.sub(r"^L/OT\s*", "LOT", venue)
        venue = re.sub(r"^LOT\s+", "LOT", venue)
        venue = re.sub(r"^JQB\s*(\d+)$", r"JQB\1", venue)
        venue = re.sub(r"^GCB FFR(\d)", r"GCB FF R\1", venue)
        venue = re.sub(r"^GCB FF RM(\d)", r"GCB FF R\1", venue)
        
        return venue
    
    def _extract_level(self, cell: str) -> Optional[int]:
        """Extract 3-digit level from cell"""
        match = re.search(r"\d{3}", cell)
        return int(match.group()) if match else None
    
    def _extract_course_kind(self, subject: str) -> Optional[str]:
        """Extract course kind (C/E) from subject"""
        if "(C)" in subject:
            return "C"
        elif "(E)" in subject:
            return "E"
        return None
