module.exports = {
  entry: ['./src/geotillsyn.js'],
  module: {
    rules: [{
      test: /\.(js)$/,
      exclude: /node_modules/
    }]
  },
  externals: ['Origo'],
  resolve: {
    extensions: ['*', '.js']
  }
};
