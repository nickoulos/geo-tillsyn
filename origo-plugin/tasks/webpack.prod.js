const { merge } = require('webpack-merge');
const path = require('path');
const common = require('./webpack.common.js');

module.exports = merge(common, {
  mode: 'production',
  output: {
    path: path.resolve(__dirname, '../build/js'),
    filename: 'geotillsyn.min.js',
    library: 'GeoTillsyn',
    libraryTarget: 'var',
    libraryExport: 'default'
  },
  devtool: false
});
