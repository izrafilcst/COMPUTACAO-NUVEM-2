# Guia AWS para o aluno: EC2, runner, deploy e encerramento

Este guia cobre tudo o que é feito no console da AWS, no terminal da EC2 e na tela de Runners do GitHub. O restante (código, PRs, CI) já está pronto ou é feito pelo Claude.

**Resultado final desejado:** uma EC2 Ubuntu com Docker e um runner do GitHub chamado `ec2-prod`, que recebe o deploy automático; evidências (prints) sem erro; recursos encerrados no fim.

## 0. Antes de começar

### 0.1 Nomes usados (copie exatamente)
| Item | Valor |
|---|---|
| Repositório | `izrafilcst/COMPUTACAO-NUVEM-2` |
| Imagem | `ghcr.io/izrafilcst/computacao-nuvem-2:<SHA>` |
| Key pair | `cn2-key` |
| Security Group | `cloud-tasks-sg` |
| Instância | `cloud-tasks-ec2` |
| Runner | `ec2-prod` (nome e label) |
| Container | `cloud-tasks-api` |
| Volume Docker | `cloud-tasks-data` |

### 0.2 Regras de ouro
1. **Porta 22 (SSH) nunca com origem `0.0.0.0/0`.** Só o seu IP (`/32`).
2. **Nunca apareça em print ou no chat:** conteúdo do arquivo `.pem`, token do runner (aparece no comando `./config.sh`), chaves de acesso da AWS (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`), senhas, painel "AWS Details" de laboratórios.
3. **Não desligue (Stop) e religue a instância** entre a entrega e a avaliação: o IP público muda.
4. Faça tudo **na mesma região** da AWS. Anote qual (sugestão: a mais próxima ou a indicada pelo professor).
5. Se o ambiente limitar região ou tipo de instância, use o permitido e registre no relatório.

### 0.3 Regras de qualidade de TODO print (confira antes de salvar)
| # | Confira | Por quê |
|---|---|---|
| 1 | A **região** aparece no canto superior direito do console | Prova que o recurso é o certo |
| 2 | **Nenhum banner vermelho ou amarelo** (erro, aviso de permissão, "failed") | Print com erro não vale como evidência |
| 3 | O estado é **final** (`Running`, `Idle`, `Terminated`), não `Pending`, `Initializing`, `Queued` | Espere e atualize a página (F5) antes |
| 4 | Nada sensível (item 2 das regras de ouro) | Repositório é público |
| 5 | Zoom do navegador em 100%, tela legível; em navegador **inclua a barra de endereço**; em terminal **inclua o comando e a saída**, com o prompt visível | Mostra onde e o que foi executado |

No terminal, o prompt `ubuntu@ip-...:~$` prova que o comando rodou **na EC2**. O prompt do seu computador (`usuario@maquina`) prova que rodou **no seu PC**. Cada print deve deixar isso claro.

### 0.4 Onde salvar os prints
Pasta `docs/evidencias/` (crie se não existir), com o nome indicado em cada print (`NN-descricao.png`). A tabela do apêndice B resume todos.

### 0.5 Quando avisar o Claude
- **Ponto A**, no fim da seção 5: envie o **IP público** e confirme que o runner está `Idle`. O Claude então faz o merge do PR do CD (primeiro deploy).
- **Ponto B**, depois da seção 6: confirme que o `/health` respondeu no navegador. O Claude então faz o merge do PR do `DELETE`.
- **Ponto C**, depois da seção 7: envie os resultados da persistência.

---

## 1. Entrar no console e escolher a região

**Onde:** console AWS (`console.aws.amazon.com`), barra superior.

1. Entre com a conta de teste fornecida pelo professor.
2. No canto superior direito, clique no nome da região e escolha a região definida na regra 4. Anote-a.
3. Na barra de busca, digite `EC2` e abra **EC2**.

**Resultado esperado:** painel **EC2 Dashboard** carregado, sem banner de erro, com a região escolhida no canto superior direito.

Se aparecer "You are not authorized to perform this operation" ou "UnauthorizedOperation": **não insista**. Tire print do erro **apenas para enviar ao professor** (não entra no relatório) e peça a permissão.

---

## 2. Rede e acesso: par de chaves e Security Group

### 2.1 Descobrir o seu IP (no seu PC)
```bash
curl -4 -s https://checkip.amazonaws.com
```
**Esperado:** uma linha com um IPv4, por exemplo `203.0.113.10`. Guarde; você vai comparar com o que o console mostrar em "My IP".

### 2.2 Criar o par de chaves
**Onde:** EC2 > menu lateral **Network & Security** > **Key pairs** > botão **Create key pair**.

1. **Name:** `cn2-key`.
2. **Key pair type:** `ED25519`.
3. **Private key file format:** `.pem`.
4. Clique em **Create key pair**. O navegador baixa `cn2-key.pem` automaticamente.

**Resultado esperado:** banner verde "Successfully created key pair" e `cn2-key` na lista.

**PRINT P01** (`01-key-pair.png`): lista de **Key pairs**.
- Deve aparecer: linha `cn2-key`, tipo `ed25519`, região visível.
- Não pode aparecer: o arquivo `.pem` aberto, banner de erro.

### 2.3 Guardar a chave com permissão correta (no seu PC)
**Linux/macOS:**
```bash
mkdir -p ~/.ssh && mv ~/Downloads/cn2-key.pem ~/.ssh/ && chmod 400 ~/.ssh/cn2-key.pem
ls -l ~/.ssh/cn2-key.pem
```
**Esperado:** a linha do `ls` começa com `-r--------`.

**Windows (PowerShell):**
```powershell
mkdir $env:USERPROFILE\.ssh -Force
Move-Item $env:USERPROFILE\Downloads\cn2-key.pem $env:USERPROFILE\.ssh\
icacls $env:USERPROFILE\.ssh\cn2-key.pem /inheritance:r
icacls $env:USERPROFILE\.ssh\cn2-key.pem /grant:r "$($env:USERNAME):(R)"
```
Nos comandos seguintes, troque `~/.ssh/cn2-key.pem` por `$env:USERPROFILE\.ssh\cn2-key.pem`.

### 2.4 Criar o Security Group
**Onde:** EC2 > **Network & Security** > **Security Groups** > **Create security group**.

1. **Security group name:** `cloud-tasks-sg`. **Description:** `API de tarefas CI/CD`. **VPC:** a padrão (deixe como está).
2. Em **Inbound rules**, clique **Add rule** duas vezes:
   - Regra 1: **Type** `SSH`, **Source** `My IP`.
   - Regra 2: **Type** `HTTP`, **Source** `My IP`.
3. Em **Outbound rules**, não mexa (padrão: tudo liberado; o runner precisa de saída para o GitHub).
4. Clique em **Create security group**.

**Resultado esperado:** banner verde "Security group (sg-...) was created successfully". Na aba **Inbound rules**, o campo **Source** mostra o seu IP terminando em `/32`, igual ao do passo 2.1.

**PRINT P02** (`02-sg-inbound.png`): Security Groups > `cloud-tasks-sg` > aba **Inbound rules**.
- Deve aparecer: porta `22` e porta `80`, ambas com origem `<seu IP>/32`; nome `cloud-tasks-sg`.
- Não pode aparecer: `0.0.0.0/0` na porta 22 (se aparecer, edite a regra antes do print).

Se o "My IP" do console mostrar um IP **diferente** do passo 2.1 (VPN ligada, por exemplo), desligue a VPN e refaça.

---

## 3. Criar a instância EC2

**Onde:** EC2 > **Instances** > botão laranja **Launch instances**. **Anote a data e a hora agora** (vão para o registro de custos, apêndice C).

Preencha, de cima para baixo:
1. **Name:** `cloud-tasks-ec2`.
2. **Application and OS Images:** clique em **Ubuntu** e escolha **Ubuntu Server 24.04 LTS (HVM), SSD Volume Type**. Em **Architecture**, `64-bit (x86)`.
3. **Instance type:** `t3.micro`. Confira se aparece o selo "Free tier eligible" e **leia o preço por hora da região** no próprio console ou na página oficial de preços do EC2; anote para o relatório.
4. **Key pair (login):** selecione `cn2-key`.
5. **Network settings** > **Edit**:
   - **Auto-assign public IP:** `Enable`.
   - **Firewall (security groups):** `Select existing security group` e marque `cloud-tasks-sg`.
6. **Configure storage:** `16` GiB, tipo `gp3`.
7. Deixe **Advanced details** como está (sem IAM instance profile).
8. Confira o painel **Summary** à direita e clique em **Launch instance**.

**Resultado esperado:** tela "Success: Successfully initiated launch of instance (i-...)". Clique em **View all instances**.

Aguarde 2 a 3 minutos e atualize (F5) até:
- **Instance state:** `Running`.
- **Status check:** `2/2 checks passed`.

**PRINT P03** (`03-instancia-running.png`): lista de **Instances**.
- Deve aparecer: `cloud-tasks-ec2`, `Running`, `2/2 checks passed`, tipo `t3.micro`, uma coluna **Public IPv4 address** preenchida.
- Não pode aparecer: `Pending`, `Initializing`, `1/2 checks passed`.

Anote o **Public IPv4 address**. Daqui em diante, `<IP_PUBLICO>` é esse valor. **Não crie Elastic IP.**

---

## 4. Acessar a EC2 e instalar o Docker

### 4.1 Conectar por SSH (no seu PC)
```bash
ssh -i ~/.ssh/cn2-key.pem ubuntu@<IP_PUBLICO>
```
Na primeira vez aparece "The authenticity of host ... can't be established" e a pergunta "Are you sure you want to continue connecting?". Digite `yes` e Enter.

**Opcional (mais seguro):** confira a fingerprint exibida com a do boot da instância: EC2 > selecione a instância > **Actions** > **Monitor and troubleshoot** > **Get system log** e procure o bloco `SSH HOST KEY FINGERPRINTS`.

**Resultado esperado:** mensagem "Welcome to Ubuntu 24.04...", e o prompt muda para `ubuntu@ip-172-31-x-x:~$`.

**PRINT P04** (`04-ssh-conectado.png`): terminal com o comando `ssh ...` e o banner de boas-vindas.
- Deve aparecer: comando `ssh -i ~/.ssh/cn2-key.pem ubuntu@<IP>`, "Welcome to Ubuntu 24.04", prompt `ubuntu@ip-...`.
- Não pode aparecer: conteúdo da chave, `Permission denied`, `Connection timed out`.

### 4.2 Copiar o script de instalação (no seu PC, **outro terminal**, na pasta do projeto)
```bash
scp -i ~/.ssh/cn2-key.pem scripts/setup-ec2-ubuntu.sh ubuntu@<IP_PUBLICO>:~/
```
**Esperado:** uma linha `setup-ec2-ubuntu.sh ... 100%`.

### 4.3 Instalar o Docker (na EC2)
```bash
bash setup-ec2-ubuntu.sh
```
Leva de 1 a 3 minutos. **Esperado nas últimas linhas:** `Docker installed. Log out and back in for group membership to take effect.` e o aviso `WARNING: docker group membership provides root-equivalent privileges.` (o aviso é normal).

Se aparecer `Could not get lock /var/lib/dpkg/lock-frontend`: o Ubuntu ainda está se atualizando no primeiro boot. Espere 2 minutos e rode de novo.

Agora **saia e entre de novo** (o grupo `docker` só vale em uma nova sessão):
```bash
exit
ssh -i ~/.ssh/cn2-key.pem ubuntu@<IP_PUBLICO>
```

### 4.4 Validar o Docker sem sudo (na EC2)
```bash
docker --version
docker ps
groups
```
**Esperado:**
- `docker --version`: `Docker version <número>, build <código>`.
- `docker ps`: só o cabeçalho `CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES`, sem linhas e **sem erro**.
- `groups`: a lista contém `docker`.

**PRINT P05** (`05-docker-sem-sudo.png`):
- Deve aparecer: os três comandos e as saídas acima, prompt `ubuntu@ip-...`.
- Não pode aparecer: `permission denied while trying to connect to the Docker daemon socket` (se aparecer, você não saiu e entrou de novo: refaça o 4.3).

### 4.5 Criar o swap de 1 GB (na EC2)
A `t3.micro` tem 1 GB de RAM; o swap evita travar durante o `docker pull`.
```bash
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```
**Esperado:** o `mkswap` imprime `Setting up swapspace version 1, size = 1024 MiB`; o `free -h` mostra a linha `Swap:` com total `1.0Gi`.

**PRINT P06** (`06-swap.png`): saída do `free -h`.
- Deve aparecer: linha `Swap:` com `1.0Gi` no total.
- Não pode aparecer: `Swap: 0B`.

---

## 5. Registrar o runner `ec2-prod`

O runner é um programa na EC2 que **liga de dentro para o GitHub** e executa o deploy. Por isso a porta 22 não precisa ficar aberta para o GitHub.

### 5.1 Abrir a tela de registro (no navegador)
**Onde:** repositório no GitHub > **Settings** > **Actions** > **Runners** > botão verde **New self-hosted runner**. Escolha **Linux** e **x64**.

A tela mostra duas seções: **Download** e **Configure**, com comandos prontos. **Use sempre os comandos da tela** (a versão do runner muda). O formato é este:

### 5.2 Baixar e extrair (na EC2)
```bash
mkdir actions-runner && cd actions-runner
curl -o actions-runner-linux-x64-<versão>.tar.gz -L https://github.com/actions/runner/releases/download/v<versão>/actions-runner-linux-x64-<versão>.tar.gz
echo "<hash>  actions-runner-linux-x64-<versão>.tar.gz" | shasum -a 256 -c
tar xzf ./actions-runner-linux-x64-<versão>.tar.gz
```
**Esperado:** o `shasum` imprime `actions-runner-linux-x64-<versão>.tar.gz: OK`. Se imprimir `FAILED`, **pare**: apague o arquivo e baixe de novo.

### 5.3 Configurar (na EC2, **sem sudo**)
Rode o `./config.sh --url https://github.com/izrafilcst/COMPUTACAO-NUVEM-2 --token <TOKEN>` da tela e responda:
| Pergunta | Resposta |
|---|---|
| `Enter the name of the runner group...` | Enter (Default) |
| `Enter the name of runner:` | `ec2-prod` |
| `Enter any additional labels` | `ec2-prod` |
| `Enter name of work folder:` | Enter (`_work`) |

**Esperado no final:** `Runner successfully added`, `Runner connection is good` e `Settings Saved.`

Se aparecer `Must not run with sudo`: você usou `sudo`; rode sem. Se aparecer `Http response code: NotFound` ou erro de token: o token expirou (vale cerca de 1 hora). Volte à tela do GitHub, copie o comando novo.

**Antes de qualquer print, limpe o terminal com `clear`:** o comando de configuração contém o token.

### 5.4 Instalar como serviço (na EC2, **com sudo**)
```bash
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```
Não use `./run.sh`: ele prende o terminal e para quando você fecha.

**Esperado no `status`:** linha `Active: active (running)` (em verde) e o nome `actions.runner.izrafilcst-COMPUTACAO-NUVEM-2.ec2-prod.service`. Saia do `status` com `q`.

**PRINT P08** (`08-runner-servico.png`): saída do `sudo ./svc.sh status`.
- Deve aparecer: `active (running)`, nome do serviço com `ec2-prod`, prompt `ubuntu@ip-...`.
- Não pode aparecer: `inactive (dead)`, `failed`, o comando `./config.sh` com token.

### 5.5 Conferir no GitHub
Volte à página **Settings > Actions > Runners** e atualize (F5).

**Resultado esperado:** o runner `ec2-prod` com status **Idle** (bolinha verde) e labels `self-hosted`, `Linux`, `X64`, `ec2-prod`.

**PRINT P07** (`07-runner-idle.png`): página de Runners.
- Deve aparecer: `ec2-prod`, `Idle`, os 4 labels, barra de endereço com o repositório.
- Não pode aparecer: `Offline`, o token ou a tela "New self-hosted runner" aberta.

### >>> Ponto A: avise o Claude
Envie: **IP público** e "runner Idle". O Claude faz o merge do PR do CD, que dispara o primeiro deploy.

---

## 6. Conferir o primeiro deploy

Depois do merge, o CD roda sozinho (cerca de 1 a 2 minutos).

### 6.1 Run do CD no GitHub
**Onde:** repositório > aba **Actions** > workflow **CD - deploy EC2** > o run mais recente > job **deploy**.

**Resultado esperado:** todos os passos com ✓ verde, incluindo **Deploy da imagem imutavel** e **Verificar /health e /version**. Expanda o último e veja `{"status":"ok"}` e `versao em execucao: {"version":"<40 caracteres>"}`.

**PRINT P09** (`09-cd-verde.png`):
- Deve aparecer: run com ✓ verde, job `deploy` com todos os passos verdes, passo de verificação expandido com o `/health` e o `/version`.
- Não pode aparecer: `Queued`, `Waiting for a runner to pick up this job`, ✗ vermelho.

Se o job ficar em `Waiting for a runner`: o runner caiu. Na EC2, `sudo ./svc.sh status` e, se preciso, `sudo ./svc.sh start`.
Se o passo de login/pull falhar com `denied`: avise o Claude (pode ser necessário deixar o pacote público em GitHub > Packages > `computacao-nuvem-2` > **Package settings** > **Change visibility**).

### 6.2 Abrir a API no navegador (no seu PC)
Digite **`http://`** explicitamente (sem `s`):
- `http://<IP_PUBLICO>/health` deve mostrar `{"status":"ok"}`.
- `http://<IP_PUBLICO>/version` deve mostrar `{"version":"<40 caracteres>"}`.

O aviso "Não seguro" do navegador é **esperado** (não há TLS neste trabalho). Se o navegador trocar para `https://` sozinho e falhar, digite `http://` de novo.

Confira que a versão é a do último commit da `main`:
```bash
git fetch origin && git log -1 --format=%H origin/main
```
**Esperado:** o mesmo valor de 40 caracteres do `/version`.

**PRINT P10a** (`10a-health.png`) e **P10b** (`10b-version.png`):
- Deve aparecer: barra de endereço com `http://<IP>/health` (ou `/version`) e o JSON esperado.
- Não pode aparecer: "Não é possível acessar esse site", `ERR_CONNECTION_TIMED_OUT`, página em branco.

Se o `/health` não abrir: confira, na ordem, (1) o seu IP não mudou (compare com `checkip.amazonaws.com` e a regra da porta 80 no SG), (2) o container está no ar (item 6.3), (3) a URL começa com `http://`.

### 6.3 Container na EC2 (na EC2)
```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
```
**Esperado:** uma linha com `cloud-tasks-api`, imagem `ghcr.io/izrafilcst/computacao-nuvem-2:<40 caracteres>`, `Up ...` e `0.0.0.0:80->8000/tcp`.

**PRINT P11** (`11-docker-ps-ec2.png`):
- Deve aparecer: o comando, a linha do `cloud-tasks-api` com a tag igual ao `/version`, prompt `ubuntu@ip-...`.
- Não pode aparecer: `Restarting`, `Exited`, tabela sem linhas.

### >>> Ponto B: avise o Claude
Diga "`/health` respondeu". O Claude faz o merge do PR do `DELETE` (segundo deploy).

---

## 7. Prova de persistência (na EC2 e no seu PC)

Objetivo: mostrar que os dados continuam depois que o container é **destruído e recriado**.

### 7.1 Configuração que garante a persistência (na EC2)
```bash
docker exec cloud-tasks-api printenv DB_PATH
docker inspect -f '{{json .Mounts}}' cloud-tasks-api
docker exec cloud-tasks-api ls -l /data
```
**Esperado:**
- `/data/tasks.db`
- JSON com `"Type":"volume"`, `"Name":"cloud-tasks-data"` e `"Destination":"/data"`
- `ls` mostra o arquivo `tasks.db`

**PRINT P12** (`12-persistencia-config.png`): os 3 comandos e as saídas.
- Não pode aparecer: `Error: No such container`, `No such file or directory`.

### 7.2 Criar dados e guardar o "antes" (no seu PC)
```bash
IP=<IP_PUBLICO>
curl -s -X POST http://$IP/tasks -H 'Content-Type: application/json' -d '{"title":"persistencia 1"}'
curl -s -X POST http://$IP/tasks -H 'Content-Type: application/json' -d '{"title":"persistencia 2"}'
curl -s http://$IP/tasks > antes.json && cat antes.json
```
**Esperado:** cada `POST` devolve `{"done":false,"id":N,"title":"..."}`; o `cat` mostra as tarefas com os mesmos `id`.

Na **EC2**, anote o container atual:
```bash
docker ps --format '{{.ID}} {{.CreatedAt}}'
```

### 7.3 Destruir o container (na EC2)
```bash
docker rm -f cloud-tasks-api
docker ps -a
docker volume ls
```
**Esperado:** o `docker ps -a` **não** lista `cloud-tasks-api`; o `docker volume ls` **ainda** lista `cloud-tasks-data`.

### 7.4 Recriar pelo CD (no GitHub)
**Onde:** Actions > **CD - deploy EC2** > run mais recente > botão **Re-run all jobs** (canto superior direito) > confirme.

**Esperado:** o novo run termina com ✓ verde em 1 a 2 minutos.

### 7.5 Comparar o "depois" (no seu PC e na EC2)
No PC:
```bash
curl -s http://$IP/tasks > depois.json
diff antes.json depois.json && echo "IGUAIS: dados preservados"
```
**Esperado:** o `diff` não imprime nada e aparece `IGUAIS: dados preservados`.

Na EC2:
```bash
docker ps --format '{{.ID}} {{.CreatedAt}}'
docker volume inspect cloud-tasks-data
```
**Esperado:** o **ID do container é outro** (prova de que foi recriado) e o volume `cloud-tasks-data` continua com `Mountpoint` em `/var/lib/docker/volumes/...`.

**PRINT P13** (`13-persistencia-antes-depois.png`): um print (ou dois lado a lado) com:
- No PC: `cat antes.json`, `diff antes.json depois.json` sem diferenças e `IGUAIS: dados preservados`.
- Na EC2: o ID do container **antes** e **depois** diferentes.
- Não pode aparecer: `diff` mostrando linhas `<`/`>`, `curl: (7) Failed to connect`, `antes.json` vazio.

### >>> Ponto C: avise o Claude
Envie "persistência ok" e cole as saídas do 7.5 (sem segredos).

---

## 8. Acesso do professor na avaliação

Combine com o professor a data e a hora. **Antes dela:**

1. **Onde:** EC2 > Security Groups > `cloud-tasks-sg` > aba **Inbound rules** > **Edit inbound rules**.
2. Na regra **HTTP (80)**, troque **Source** de `My IP` para `Anywhere-IPv4` (`0.0.0.0/0`). **Mantenha a regra SSH (22) em `My IP`.**
3. **Save rules.** O console avisa que `0.0.0.0/0` libera o acesso a todos: para a porta 80 isso é esperado e aceitável (dados fictícios, sem TLS).

**PRINT P14** (`14-sg-professor.png`): Inbound rules.
- Deve aparecer: porta 80 com `0.0.0.0/0` e porta 22 com `<seu IP>/32`.
- Não pode aparecer: porta 22 com `0.0.0.0/0`.

4. **Teste de fora da sua rede:** no celular, desligue o Wi-Fi (dados móveis) e abra `http://<IP_PUBLICO>/health`.

**PRINT P15** (`15-teste-externo.png`): captura do celular.
- Deve aparecer: `http://<IP>/health`, `{"status":"ok"}`, indicador de dados móveis.
- Não pode aparecer: página de erro ou conexão pelo Wi-Fi de casa.

5. Confira: instância `Running`, runner `Idle`, `docker ps` com o container no ar. Envie o IP ao professor no Moodle. **Não pare a instância** até a avaliação terminar.
6. Depois da avaliação, volte a regra 80 para `My IP`.

---

## 9. Encerramento e custos

Faça **só depois** da avaliação. A ordem importa (o runner precisa sair antes da instância; o Security Group só apaga depois da instância).

### 9.1 Remover o runner do GitHub
1. Na EC2: `cd ~/actions-runner && sudo ./svc.sh stop && sudo ./svc.sh uninstall`.
2. No GitHub: **Settings > Actions > Runners** > `ec2-prod` > menu `...` > **Remove runner**. A tela mostra o comando com token de remoção; rode-o na EC2: `./config.sh remove --token <TOKEN_DE_REMOCAO>`.
3. Se a instância já não existir, use **Force remove this runner**.

**PRINT P16** (`16-runner-removido.png`): página de Runners.
- Deve aparecer: lista **sem** `ec2-prod`.
- Não pode aparecer: `ec2-prod` como `Offline` (isso é um runner esquecido).

### 9.2 Terminar a instância
**Onde:** EC2 > Instances > marque `cloud-tasks-ec2` > **Instance state** > **Terminate (delete) instance** > confirme. **Terminate**, não Stop: Stop mantém o disco cobrando.

**Esperado:** `Shutting-down` e, em cerca de 1 minuto, `Terminated` (a linha fica visível por cerca de 1 hora).

**PRINT P17** (`17-instancia-terminated.png`):
- Deve aparecer: `cloud-tasks-ec2`, `Terminated`, ID da instância, região.
- Não pode aparecer: `Running`, `Shutting-down`, `Stopped`.

### 9.3 Apagar o que sobrou
1. **Volumes:** EC2 > Elastic Block Store > **Volumes**. O volume raiz some sozinho. Se aparecer algum `Available`, selecione > **Actions** > **Delete volume**.
2. **Elastic IPs** e **Snapshots**: confirme que estão vazios (não deveria haver nada).
3. **Security Groups:** apague `cloud-tasks-sg` (Actions > Delete security groups). O grupo `default` não se apaga e é normal que fique.
4. **Key pairs:** apague `cn2-key` (Actions > Delete). No seu PC: `shred -u ~/.ssh/cn2-key.pem` (ou apague o arquivo).
5. GitHub > Packages: opcional apagar as versões da imagem.

### 9.4 Prova de que nada sobrou
**Onde:** EC2 > **Dashboard**, painel **Resources** (na região usada). Opcional: **EC2 Global view** para ver todas as regiões.

**PRINT P18** (`18-recursos-zerados.png`):
- Deve aparecer: Instances (running) `0`, Instances `0`, Volumes `0`, Elastic IPs `0`, Key pairs `0`, Snapshots `0`, Security groups `1` (o `default`), região visível.
- Não pode aparecer: qualquer valor diferente desses (corrija antes do print).

### 9.5 Custo (no dia seguinte)
**Onde:** Billing and Cost Management > **Cost Explorer**. Período: dos dias de uso até hoje; **Group by: Service**. Os dados podem levar até 24 horas para aparecer.

**PRINT P19** (`19-custos.png`):
- Deve aparecer: gráfico com o custo por serviço (EC2) até o dia do encerramento e **sem custo novo depois** dele.
- Não pode aparecer: serviços inesperados (NAT Gateway, Elastic IP, Load Balancer), valores que continuam subindo depois de terminar.

Se aparecer algo inesperado, procure o recurso e apague antes de avisar. Se a conta não der acesso ao Cost Explorer, registre isso no relatório e use a tela de **Bills** ou o que o professor indicar.

Depois, envie ao Claude: data/hora da terminação, ID da instância e do volume, e os prints P16 a P19, para atualizar o relatório.

---

## Apêndice A: erros comuns e o que fazer (nunca tire print como evidência de um erro)

| Sintoma | Causa provável | Solução |
|---|---|---|
| `WARNING: UNPROTECTED PRIVATE KEY FILE!` | Permissão da chave | `chmod 400 ~/.ssh/cn2-key.pem` |
| `Permission denied (publickey)` | Usuário ou chave errados | Usuário é `ubuntu`; use `-i ~/.ssh/cn2-key.pem` |
| `Connection timed out` no SSH | Seu IP mudou, regra 22 errada, instância parada | Compare `checkip.amazonaws.com` com a regra 22 e edite o SG |
| `Connection refused` | Instância ainda iniciando | Espere o `2/2 checks passed` |
| `Could not get lock ... dpkg` | Atualização do primeiro boot | Espere 2 minutos e repita |
| `permission denied ... docker.sock` | Não saiu e entrou após instalar o Docker | `exit` e conecte de novo |
| `Must not run with sudo` no `config.sh` | Usou `sudo` | Rode sem `sudo` |
| Erro de token no `config.sh` | Token expirou | Gere um novo na tela "New self-hosted runner" |
| Runner `Offline` | Serviço parado | `sudo ./svc.sh start` na EC2 |
| Job do CD em `Waiting for a runner` | Runner offline ou label errado | Veja `Offline` acima; label deve ser `ec2-prod` |
| Navegador não abre `/health` | `https://` automático, IP mudou, container parado | Use `http://`, confira a regra 80 e o `docker ps` |
| `UnauthorizedOperation` no console | Permissão da conta de teste | Fale com o professor; não tente contornar |
| Custo inesperado | Recurso esquecido | Procure no Dashboard e na Global view e apague |

## Apêndice B: lista de prints

| ID | Arquivo | Onde | Mostra |
|---|---|---|---|
| P01 | `01-key-pair.png` | Console, Key pairs | `cn2-key` ed25519 |
| P02 | `02-sg-inbound.png` | Console, SG | 22 e 80 só com `/32` |
| P03 | `03-instancia-running.png` | Console, Instances | Running, 2/2 checks |
| P04 | `04-ssh-conectado.png` | Terminal do PC | Welcome to Ubuntu 24.04 |
| P05 | `05-docker-sem-sudo.png` | Terminal da EC2 | `docker ps` sem erro, `docker` em `groups` |
| P06 | `06-swap.png` | Terminal da EC2 | Swap 1.0Gi |
| P07 | `07-runner-idle.png` | GitHub, Runners | `ec2-prod` Idle |
| P08 | `08-runner-servico.png` | Terminal da EC2 | serviço `active (running)` |
| P09 | `09-cd-verde.png` | GitHub, Actions | CD verde com `/health` e `/version` |
| P10a/b | `10a-health.png`, `10b-version.png` | Navegador | JSON esperado com `http://` |
| P11 | `11-docker-ps-ec2.png` | Terminal da EC2 | container Up, tag = SHA |
| P12 | `12-persistencia-config.png` | Terminal da EC2 | `DB_PATH`, volume, `tasks.db` |
| P13 | `13-persistencia-antes-depois.png` | PC e EC2 | `diff` vazio, container novo |
| P14 | `14-sg-professor.png` | Console, SG | 80 aberta, 22 só `/32` |
| P15 | `15-teste-externo.png` | Celular | `/health` fora da sua rede |
| P16 | `16-runner-removido.png` | GitHub, Runners | sem `ec2-prod` |
| P17 | `17-instancia-terminated.png` | Console, Instances | Terminated |
| P18 | `18-recursos-zerados.png` | Console, EC2 Dashboard | recursos em 0 |
| P19 | `19-custos.png` | Console, Cost Explorer | custo parado |

## Apêndice C: registro de custos (preencha durante o trabalho)

| Campo | Valor |
|---|---|
| Região | |
| Tipo da instância | `t3.micro` |
| Preço por hora (fonte: página oficial de preços do EC2 ou console, na região) | |
| Início (data e hora, passo 3) | |
| Fim (data e hora, passo 9.2) | |
| Horas de uso | |
| Disco EBS | gp3, 16 GiB |
| Elastic IP | não usado |
| Custo mostrado no Cost Explorer (passo 9.5) | |
| Recursos que sobraram | nenhum (P18) |
