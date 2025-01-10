# CI/CD com GitHub Actions no Azure Web App (Dev, QA e Prod)

https://medium.com/@lorenzouriel/ci-cd-with-github-actions-on-azure-web-app-dev-qa-and-prod-241c1cadd9b6

Este repositório contém a configuração de pipelines CI/CD para gerenciar os ambientes de **Desenvolvimento (Dev)**, **Qualidade (QA)** e **Produção (Prod)** no Azure Web Apps, utilizando arquivos YAML.

## Ambientes e Pipelines
### Dev
O pipeline de Dev é acionado sempre que há um push para a branch `dev`. Ele faz o build e deploy da aplicação para o ambiente de Desenvolvimento e cria um Pull Request (PR) para a branch `qa` para revisão e testes adicionais.

> Link do site em Dev: https://yellow-stone-0f93d7c0f.5.azurestaticapps.net

### QA
O pipeline de QA é acionado quando um Pull Request para a branch `qa` é fechado. Este pipeline realiza o build e deploy da aplicação para o ambiente de Qualidade.

> Link do site em QA: https://witty-glacier-09a3fa10f.5.azurestaticapps.net

### Prod
O pipeline de Prod é acionado quando um Pull Request para a branch `main` é fechado. Este pipeline faz o build e deploy da aplicação para o ambiente de Produção e também fecha o Pull Request se for apropriado.

> Link do site em Prod: https://lively-grass-003c4aa0f.5.azurestaticapps.net

## Passos para Configuração
**Crie Repositórios e Branches:** Garanta que você tenha os repositórios e branches (`dev`, `qa`, `main`) configurados no GitHub.

**Configuração de Secrets:** No seu repositório GitHub, adicione os seguintes segredos nas configurações:
* `AZURE_STATIC_WEB_APPS_API_TOKEN_YELLOW_STONE_0F93D7C0F` (Ambiente de Dev)
* `AZURE_STATIC_WEB_APPS_API_TOKEN_WITTY_GLACIER_09A3FA10F` (Ambiente de QA)
* `AZURE_STATIC_WEB_APPS_API_TOKEN_LIVELY_GRASS_003C4AA0F` (Ambiente de Prod)
* `GITHUB_TOKEN` (Token para conexão com Azure)

**Configure os Webhooks:** Certifique-se de que seu repositório GitHub esteja configurado para acionar os pipelines conforme as branches e eventos especificados.

## Arquitetura
![architecture](/docs/architecture.png)

## 💻 Projeto - Save Walter White
O projeto do Save Walter White é de autoria de [Tatiana Emília Moreno](https://www.linkedin.com/in/tatmorenno/).

<h1 align="center">
   <br/><br/>
  <kbd>
  <img src="https://ik.imagekit.io/tatmorenno/Walter_White_29aseVhlz.png" height="300" width="350">
  </kbd>
</h1>
<br/>

# CI/CD with GitHub Actions on Azure Web App (Dev, QA and Prod)
This repository contains the configuration of CI/CD pipelines to manage **Development (Dev)**, **Quality (QA)**, and **Production (Prod)** environments in Azure Web Apps, using YAML files.

## Environments and Pipelines 
### Dev 
The Dev pipeline is triggered whenever there is a push to the `dev` branch. It builds and deploys the application to the Development environment and creates a Pull Request (PR) to the `qa` branch for further review and testing.

### QA 
The QA pipeline is triggered when a Pull Request to a `qa` branch is closed. This pipeline builds and deploys the application to the Quality environment.

### Prod 
The Prod pipeline is triggered when a Pull Request to a `main` branch is closed. This pipeline builds and deploys the application to the Production environment and also closes the Pull Request for protection.

## Configuration Steps 
**Create Repositories and Branches:** Make sure you have the repositories and branches (`dev`, `qa`, `main`) configured in GitHub.

**Secrets Configuration:** In your GitHub repository, add the following secrets to the settings: 
* `AZURE_STATIC_WEB_APPS_API_TOKEN_YELLOW_STONE_0F93D7C0F` (Dev environment) 
* `AZURE_STATIC_WEB_APPS_API_TOKEN_WITTY_GLACIER_09A3FA10F` (QA environment) 
* `EB_APPS_API_TOKEN_LIVELY_GRASS_003C4AA0F` (Production environment) 
* `GITHUB_TOKEN ` (Token for connecting to Azure) 

**Configure Webhooks:** Make sure your GitHub repository is configured to trigger pipelines based on the specified branches and events.

## Architecture 
![architecture](/docs/architecture.png) 

## 💻 Project - Save Walter White 
The Save Walter White project was designed by [Tatiana Emília Moreno](https://www.linkedin.com/in/tatmorenno/).

<h1 align="center"> <br/><br/> <kbd> <img src="https://ik.imagekit.io/tatmorenno/Walter_White_29aseVhlz.png" height="300" width="350" > </kbd> </h1> <br/>
