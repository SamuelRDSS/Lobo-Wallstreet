#!/usr/bin/env python3
"""Compatibility launcher for the old front_server.py command."""

from __future__ import annotations

import uvicorn


if __name__ == "__main__":
    print("Iniciando Lobo Walstreet em http://localhost:8088/front/", flush=True)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8088)
