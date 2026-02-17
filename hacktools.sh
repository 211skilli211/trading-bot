#!/data/data/com.termux/files/usr/bin/bash
while true; do
    clear
    echo ""
    echo "╔═══════════════════════════════════════════╗"
    echo "║     🔧 Mobile HackLab - Quick Tools       ║"
    echo "╠═══════════════════════════════════════════╣"
    echo "║  1) 🌐 Nmap - Network Scan                ║"
    echo "║  2) 💉 SQLMap - SQL Injection             ║"
    echo "║  3) 🔑 Hydra - Password Attack            ║"
    echo "║  4) 💀 Metasploit Console                 ║"
    echo "║  5) 🖥️  Start Desktop                     ║"
    echo "║  6) 🔍 Check GPU Status                   ║"
    echo "║  0) ❌ Exit                               ║"
    echo "╚═══════════════════════════════════════════╝"
    echo ""
    read -p "  Select option: " choice
    
    case $choice in
        1) 
            read -p "  Enter target IP/hostname: " target
            nmap -sV $target
            read -p "Press Enter to continue..."
            ;;
        2) 
            read -p "  Enter vulnerable URL: " url
            sqlmap -u "$url" --batch
            read -p "Press Enter to continue..."
            ;;
        3) 
            echo "  Example: hydra -l admin -P wordlist.txt 192.168.1.1 ssh"
            read -p "Press Enter to continue..."
            ;;
        4) 
            msfconsole
            ;;
        5) 
            bash ~/start-hacklab.sh
            ;;
        6)
            echo ""
            glxinfo | grep "renderer"
            echo ""
            read -p "Press Enter to continue..."
            ;;
        0) 
            exit 0
            ;;
    esac
done
