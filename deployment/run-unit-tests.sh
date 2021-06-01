# Placeholder
#!/bin/bash
TEMPLATE_DIR=deployment
SOURCE_DIR=source
cd ..
ROOT_DIR=`pwd`
echo 'pip3 install -r source/requirements.txt -t source/'
pip3 install -r source/requirements.txt -t source/
echo 'pip3 install -r source/testing_requirements.txt'
pip3 install -r source/testing_requirements.txt
mkdir ${ROOT_DIR}/${TEMPLATE_DIR}/test/coverage-reports
echo ------------ ecs ---------------
coverage_report_path=${ROOT_DIR}/${TEMPLATE_DIR}/test/coverage-reports/ecs.coverage.xml
cd ${ROOT_DIR}/${SOURCE_DIR} && pytest tests --cov=${ROOT_DIR}/${SOURCE_DIR}/ecs --cov-report=term-missing --cov-report "xml:$coverage_report_path"
sed -i -e "s,<source>${ROOT_DIR}/${SOURCE_DIR}/ecs,<source>source/ecs,g" $coverage_report_path
echo ------------ lambda ---------------
coverage_report_path=${ROOT_DIR}/${TEMPLATE_DIR}/test/coverage-reports/lambda.coverage.xml
cd ${ROOT_DIR}/${SOURCE_DIR} && pytest tests --cov=${ROOT_DIR}/${SOURCE_DIR}/lambda --cov-report=term-missing --cov-report "xml:$coverage_report_path"
sed -i -e "s,<source>${ROOT_DIR}/${SOURCE_DIR}/lambda,<source>source/lambda,g" $coverage_report_path

cd ${ROOT_DIR}/${TEMPLATE_DIR}