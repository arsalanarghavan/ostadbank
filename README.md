# OstadBank Bot - The Professor Archive Bot

![OstadBank Banner](https://via.placeholder.com/1280x400.png?text=OstadBank+Telegram+Bot)

An advanced Telegram bot designed to create a "Professor Archive," allowing students to share their experiences with different professors and courses. This bot is built to help students make more informed decisions when selecting their classes.

The project is fully containerized using **Docker**, ensuring the installation and deployment process is simple, fast, and isolated.

---

## 🌟 Key Features

### 👤 For Users:
- **✍️ Submit Experience:** A simple, conversation-driven flow to submit detailed reviews about professors, including teaching style, notes, projects, exams, and more.
- **📖 My Experiences:** View a list of all submitted experiences and their current status (Pending, Approved, Rejected).
- **📜 View Rules:** Quickly access the rules and guidelines for using the bot.
- **🔐 Forced Channel Subscription:** An optional feature to require users to join specific channels before they can use the bot.

### 👮‍♂️ For Admins:
- **👑 Full-Featured Admin Panel:** A powerful management dashboard with an intuitive inline keyboard interface.
- **✅ Approve or Reject Submissions:** Review user-submitted experiences and either approve them (which automatically posts them to a designated channel) or reject them.
- **📊 Bot Statistics:** View detailed statistics, including the total number of users and the count of experiences in each status category.
- **📢 Broadcast Message:** Send a message to all users of the bot simultaneously.
- **👤 Direct Message a User:** Send a private message to a specific user via their numeric ID.
- **⚙️ Full CRUD Management:** Manage all aspects of the bot's data, including fields, majors, courses, professors, and even the bot's text messages.
- **🔗 Channel Management:** Add, remove, and manage channels for the forced subscription feature.
- **🛡️ Admin Management:** Add or remove other administrators.
- **🗄️ Automatic Database Backups:** Automatically sends regular database backups to a designated private Telegram channel.

---

## 🛠️ Tech Stack

- **Programming Language:** Python 3.11
- **Telegram Bot Framework:** `python-telegram-bot`
- **Database:** MariaDB (via Docker)
- **ORM:** SQLAlchemy
- **Containerization:** Docker & Docker Compose
- **Reverse Proxy & Auto SSL:** Traefik (for Webhook mode)
- **Environment Variables:** `python-dotenv`

---

## 🚀 Installation Guide (Recommended Docker Method)

Installing this project is incredibly simple thanks to the automated installation script. The script handles everything from installing Docker to prompting for configuration details and launching the bot.

### Prerequisites:
1.  A Virtual Private Server (VPS) running a Linux OS (e.g., Ubuntu 20.04 or newer).
2.  A domain or subdomain with its A record pointing to your server's IP address.

### Installation Steps:
Simply copy and paste the following command into your server's terminal:

```bash
curl -L [https://raw.githubusercontent.com/arsalanarghavan/ostadbank/main/install.sh](https://raw.githubusercontent.com/arsalanarghavan/ostadbank/main/install.sh) -o install.sh && chmod +x install.sh && sudo ./install.sh
```

The installation script will run automatically and prompt you for the following information:
- **Domain Name:** Your configured domain or subdomain (e.g., `bot.yourdomain.com`).
- **Let's Encrypt Email:** A valid email address for your SSL certificate.
- **Bot Token:** Your Telegram bot token obtained from @BotFather.
- **Owner ID:** Your numeric Telegram user ID, which will be set as the main admin.
- **Channel ID:** The ID of the channel where approved experiences will be posted (starts with `-100`).
- **Backup Channel ID:** The ID of the channel where database backups will be sent (starts with `-100`).

After you provide the details, the script will automatically configure Traefik for SSL and launch your bot in **Webhook mode** for optimal performance.

---

## 📂 Project Structure

```
/
├── .env.example        # Example environment variables file
├── config.py           # Loads environment variables and main settings
├── constants.py        # Stores constants and callback data patterns
├── database.py         # Handles all database operations via SQLAlchemy
├── docker-compose.yml  # Defines all Docker services (Traefik, App, DB)
├── Dockerfile          # Instructions to build the bot's Docker image
├── install.sh          # Fully automated installation script
├── keyboards.py        # Functions for generating Telegram keyboards
├── main.py             # The main application entry point for the bot
├── models.py           # SQLAlchemy database models
├── requirements.txt    # List of required Python libraries
└── update.sh           # Script to update the bot to the latest version
```

---

## 🤝 Contributing

Contributions are welcome! If you have an idea for an improvement or have found a bug, please open an **Issue** or submit a **Pull Request**.

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for more details.