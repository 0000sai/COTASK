// This file is intented to show off various Declarative pipeline features.

/* Credits: 
https://e.printstacktrace.blog/jenkins-pipeline-environment-variables-the-definitive-guide/
https://e.printstacktrace.blog/how-to-catch-curl-response-in-jenkins-pipeline/
https://gist.github.com/merikan/228cdb1893fca91f0663bab7b095757c



*/
// Import Shared Library
@Library('my-shared-library') _ // Imports entire library, alt specify tag or branch @Library('my-shared-library@1.0') _

def sc = new org.slib.sonarqube()

def globalVar = '' // Enables var to be used throughout pipeline


pipeline {
    agent { label 'linux' } // or agent any
    parameters {
        string(name: 'slackChannel', defaultValue: 'devops', description: 'Slack channel to report Jenkins notifications')

    }
    environment { // These vars cannot be overridden using env.varname, you can with override withEnv(["env=varname]) {}
        // All environment variables are stored as STRINGS!! even if defined as a bool for example
        JIRA_SITE="${jiraName}" // This var is automatically used by the jira-steps plugin
        MY_STRINGBOOL = false; // This is actually stored as a string, so "false".  Use 'MY_STRINGBOOL.toBoolean() == false' to evaluate as a bool
        LS = "${sh(script:'ls -lah', returnStdout: true).trim()}" // You can capture SH output within environment! Don't forget to use trim for whitespace
    }
    options {
        timestamps() // plugin: https://plugins.jenkins.io/timestamper/
        timeout(time: 1, unit: 'HOURS') // Always have a max timeout on the pipeline
        buildDiscarder(logRotator(numToKeepStr: '5')) // Only keep so many jobs, saves storage!
    }
    stages {
        stage('Initial Tasks') {
            steps {
                 script {
                    checkoutSCM // Uses repo from job configuration
                    startedBy = whoStartedJob() // Record what/who triggered pipeline (by user, git trigger, schedule etc)
                    echo "Pipeline triggered by: ${startedBy}"
                }
            }
        }
        stage('Blocking Step') {
            options { timeout(time: 1, unit: 'MINUTES') } // TODO:
            when {
                expression {
                    input message: 'Error out of pipeline?'
                    // if input is Aborted, the whole build will fail, otherwise
                    // we must return true to continue
                    return true
                }
                beforeAgent true
            }
            steps {
                script {
                    if (isUnix()) { 
                        sh "Linux agent!"
                        sh "printenv | sort"
                    }
                    else {  // use powershell() or pwsh() here?? 
                        bat "echo Windows agent!"
                        bat "set" } 
                    // https://www.jenkins.io/doc/pipeline/steps/workflow-durable-task-step/
                    // https://docs.microsoft.com/en-us/powershell/scripting/whats-new/differences-from-windows-powershell?view=powershell-7.2
                    
                    error "breaking pipeline with this error message"
            }
        }
        stage('Env vars') {
            steps {
                script {
                    env.IS_NEW_VERSION = "YES"
                    env.MY_VAR = "MY ENV VAR"
                    echo "${env.MY_VAR} works with .env and ${MY_VAR} but env. is more concise.  Built in vars work too ${env.BUILD_NUMBER}"
                    if (isUnix()) { 
                        sh "echo $MY_VAR" } // !! TODO does this work with env.MY_VAR ?
                    else { bat "echo $MY_VAR" }
                }
            }
        }
        stage('Random Stuff') {
            steps {
                echo "sleeping, because I can"
                sleep(10)
                script {
                    if (isUnix()) { 
                        // use returnStdout to capture the output, otherwise sh returns nothing
                        env.shell_output = sh(script:'ls -lah', returnStdout: true).trim()
                        echo "LS = ${env.shell_output}"
                        // or if you access env variable in the shell command
                        sh 'echo $shell_output'
                        
                    }
                }
            }
        }
        stage("Using curl example") {
            steps {
                script {
                    if (isUnix()) { 
                        final String url = "http://localhost:8080/job/Demos/job/maven-pipeline-demo/job/sdkman/2/api/json"

                        withCredentials([usernameColonPassword(credentialsId: "jenkins-api-token", variable: "API_TOKEN")]) {
                            // Use curl to also output the response code, store response and response code in separate vars by splitting new line
                            final def (String response, int code) =
                                sh(script: "curl -s -w '\\n%{response_code}' -u $API_TOKEN $url", returnStdout: true)
                                    .trim()
                                    .tokenize("\n")
                            // Curl Tips
                            // "-L" allows redirects to be followed, e.g. http to https etc
                            // "-H 'Accept:application/json'" response type
                            // "--retry-connrefused --retry 10 --retry-delay 6" Retry connection

                            echo "HTTP response status code: $code"
                            // Use JQ to manage the response
                            if (code == 200) {
                                def executingTimeMillis = sh(script: "echo '$response' | jq -r '.actions[] | select(._class == \"jenkins.metrics.impl.TimeInQueueAction\") | .executingTimeMillis'", returnStdout: true).trim()

                                echo "executingTimeMillis = $executingTimeMillis"
                            }
                        }
                    }
                }
            }
        }
        stage('More Conditionals') {
            when {
                branch "master"
                environment name: "IS_NEW_VERSION", value: "YES"
            }
            
        }
        stage("A stage to be skipped") {
            when {
                expression { false }  //skip this stage
            }
            steps {
                echo 'This step will never be run'
            }
        }
        stage("Trigger another job") {
            steps {
                build job: 'JB Deploy', wait: false, parameters: [[$class: 'StringParameterValue', name: 'BuildId', value: BUILD_ID]]}}
        }
        stage("Avance timeout handling") {
            // Keep pipeline running in the event of stage timeout, also set timed out stage status to aborted
            // source: https://e.printstacktrace.blog/how-to-time-out-jenkins-pipeline-stage-and-keep-the-pipeline-running/
            options {
                timeout(time: 3, unit: "SECONDS")
            }
            steps {
                script {
                    Exception caughtException = null

                    catchError(buildResult: 'SUCCESS', stageResult: 'ABORTED') { 
                        try { 
                            echo "Started stage A"
                            sleep(time: 5, unit: "SECONDS")
                        } catch (org.jenkinsci.plugins.workflow.steps.FlowInterruptedException e) {
                            error "Caught ${e.toString()}" 
                        } catch (Throwable e) {
                            caughtException = e
                        }
                    }

                    if (caughtException) {
                        error caughtException.message
                    }
                }
            }
        }
        
    }
    post {
        always {
            cleanWs()   // Clean up Jenkins workspace - this is a plugin
        }
        fixed {
            echo "Pipeline is now successful after previous failure"
        }
        success {
            echo "Build Successful"
        }
        failure {
            script { 
                echo "Build failed"
                // Create Jira?
                // Send Slack?
            }
        }
        aborted {
            // This stage is triggered due to a non-error termination
            // e.g. timeout being exceeded, notifications to DevOps team go here
            echo 'aborted'
        }
    }
}
