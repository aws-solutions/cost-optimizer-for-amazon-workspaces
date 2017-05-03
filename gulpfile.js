const config = require('./config/config');
const gulp = require('gulp');
const zip = require('gulp-zip');
const rename = require('gulp-rename');

gulp.task('build', () => {
  return gulp.src('src/*')
    .pipe(zip('workspaces-cost-optimizer.zip'))
    .pipe(gulp.dest('dist'));
})

gulp.task('upload', ['uploadLambda', 'uploadVersionedTemplate', 'uploadUnversionedTemplate'])

gulp.task('uploadLambda', ['build'], () => {

  var s3 = require('gulp-s3-upload')(config.s3Upload.solutionsMaster);

  return gulp.src('dist/workspaces-cost-optimizer.zip')
    .pipe(rename(config.name + '/' + config.version + '/workspaces-cost-optimizer.zip'))
    .pipe(s3({
      Bucket: config.s3Upload.solutionsMaster.bucketName,
      ACL: 'public-read'
    }))
})

gulp.task('uploadVersionedTemplate', () => {

  var s3 = require('gulp-s3-upload')(config.s3Upload.solutionsReference);
  var templateName = 'workspaces-cost-optimizer.template';

  return gulp.src('cform/' + templateName)
    .pipe(rename(config.name + '/' + config.version + '/' + templateName))
    .pipe(s3({
      Bucket: config.s3Upload.solutionsReference.bucketName,
      ACL: 'public-read'
    }))
})

gulp.task('uploadUnversionedTemplate', () => {

  var s3 = require('gulp-s3-upload')(config.s3Upload.solutionsReference);
  var templateName = 'workspaces-cost-optimizer.template';

  return gulp.src('cform/' + templateName)
    .pipe(rename(config.name + '/latest/' + templateName))
    .pipe(s3({
      Bucket: config.s3Upload.solutionsReference.bucketName,
      ACL: 'public-read'
    }))
})

gulp.task('default', ['build', 'upload']);