# Guia de configuração do laboratório (AWS Ubuntu + GitHub Actions)

## 1. Repositório
1. Crie um novo repositório a partir deste starter (com o histórico próprio do grupo).
2. Ative Actions e mantenha `main` protegida quando o plano da conta permitir.
3. Crie branch `feature/...`, envie PR e só integre após CI passar.

## 2. AWS EC2
1. Crie instância **Ubuntu Server 24.04 LTS**, arquitetura x86_64, com IP público e chave SSH. Verifique preços/limites/créditos antes de iniciar.
2. Security Group: HTTP TCP/80 de fontes permitidas para testar; SSH TCP/22 **apenas de endereços confiáveis**. Para runner GitHub hospedado (IPs variáveis), use runner auto-hospedado em rede permitida ou implemente acesso de implantação temporário/restrito com supervisão docente. **Não deixe SSH aberto para toda a internet.**
3. Conecte com SSH e execute `bash scripts/setup-ec2-ubuntu.sh` (copie o script ou clone o repositório na instância). Faça logout/login e teste `docker ps` sem sudo.
4. Certifique-se que a porta 80 está livre. Execute deploy manual primeiro, se necessário.

## 3. GitHub: runner self-hosted (sem secrets de SSH)
O CD roda em um **runner self-hosted instalado na própria EC2**, que se conecta de dentro para o GitHub. Por isso não há SSH de entrada para o deploy, nem secrets `EC2_HOST`, `EC2_SSH_KEY`, `EC2_KNOWN_HOSTS` ou variável `EC2_USER`. O SSH (porta 22) fica só para administração, liberado apenas para o IP do aluno.
1. Settings > Actions > Runners > New self-hosted runner > Linux x64; execute na EC2 os comandos mostrados na tela (o token é temporário e não deve ser compartilhado).
2. No `./config.sh`, use o nome `ec2-prod` e o label extra `ec2-prod`.
3. Instale como serviço: `sudo ./svc.sh install && sudo ./svc.sh start`.
4. Como o repositório é público, em Settings > Actions > General exija aprovação para workflows de **todos** os colaboradores externos e nunca aprove a execução de workflow vindo de fork: ele poderia tentar usar o runner.
O environment `production` é criado automaticamente na primeira execução do CD.

## 4. Registry GHCR
A CI publica imagem `ghcr.io/OWNER/REPO:COMMIT_SHA` após `push` na main. Para simplificar o laboratório, nas configurações do pacote GitHub mude a visibilidade da imagem para **Public**, de modo que EC2 execute `docker pull` sem credenciais persistentes. Não publique dados sensíveis na imagem.

## 5. Validação
- Crie PR: apenas testes/build; sem publicação ou deploy.
- Merge para `main`: CI publica imagem; evento `workflow_run` inicia CD.
- Acesse `http://IP_PUBLICO/health`, `http://IP_PUBLICO/tasks`.
- Faça nova mudança pela branch e PR e comprove novo deploy automático.
- Faça screenshot dos runs e registre URL/commit no relatório.

## 6. Diagnóstico
- Actions falhou em `docker push`: verifique `packages: write`, permissões de Actions e configuração GHCR.
- `docker pull` falhou na EC2: confira se pacote está público e se tag SHA existe.
- Falha SSH: reveja Security Group, conectividade do runner, chave, usuário e known_hosts.
- Falha HTTP: verifique SG porta 80, endereço, `docker ps` e `docker logs cloud-tasks-api`.
- **Atenção:** runner público do GitHub não possui IP fixo. Não altere o SG para 0.0.0.0/0 só para fazer o CD passar. O professor deve providenciar um runner com acesso controlado ou outra estratégia de deploy (ex.: SSM), antes da avaliação do CD.

## 7. Custos e encerramento
Desligar nem sempre elimina custo de EBS e IP; após a apresentação, exclua instância, volumes e recursos alocados conforme orientação docente.
