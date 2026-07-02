const { merge } = require('webpack-merge');
const path = require('path');
const common = require('./webpack.common.js');

module.exports = merge(common, {
  output: {
    path: path.resolve(__dirname, '../build/js'),
    filename: 'geotillsyn.js',
    library: 'GeoTillsyn',
    libraryTarget: 'var',
    libraryExport: 'default'
  },
  devServer: {
    static: path.resolve(__dirname, '../build'),
    port: 9967,
    devMiddleware: { writeToDisk: true }
  },
  devtool: 'source-map'
});
